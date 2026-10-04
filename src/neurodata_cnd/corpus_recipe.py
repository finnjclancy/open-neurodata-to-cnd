"""Load corpus recipes and validate their recording layouts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._storage import _read_json
from .recipe import CorpusPlanError


@dataclass(slots=True, frozen=True)
class CorpusExperiment:
    task: str
    template_recipe: Path
    paths: tuple[str, ...]
    primary_path: str
    metadata_path: str


@dataclass(slots=True, frozen=True)
class CorpusRecipe:
    path: Path
    corpus_id: str
    corpus_version: str
    status: str
    inventory_url: str
    inventory_sha256: str
    dataset_id: str
    provider: str
    source_version: str
    source_url: str
    source_doi: str | None
    experiments: tuple[CorpusExperiment, ...]
    participants_path: str | None


def load_corpus_recipe(path: str | Path) -> CorpusRecipe:
    """Load one dataset-level planning recipe."""
    resolved = Path(path).expanduser().resolve()
    payload = _read_json(resolved)
    inventory = _object(payload, "inventory")
    source = _object(payload, "source")
    layout = _object(payload, "layout")
    digest = str(inventory["canonical_sha256"]).lower()
    if not _hex_digest(digest, 64):
        raise CorpusPlanError(
            "inventory.canonical_sha256 must be a hexadecimal SHA-256"
        )
    experiments = _corpus_experiments(resolved, payload, layout)
    return CorpusRecipe(
        path=resolved,
        corpus_id=str(payload["corpus_id"]),
        corpus_version=str(payload["corpus_version"]),
        status=str(payload["status"]),
        inventory_url=str(inventory["url"]),
        inventory_sha256=digest,
        dataset_id=str(source["dataset_id"]),
        provider=str(source["provider"]),
        source_version=str(source["version"]),
        source_url=str(source["url"]),
        source_doi=str(source["doi"]) if source.get("doi") else None,
        experiments=experiments,
        participants_path=(
            str(layout["participants_path"])
            if layout.get("participants_path")
            else None
        ),
    )


def _corpus_experiments(
    recipe_path: Path, payload: dict[str, Any], layout: dict[str, Any]
) -> tuple[CorpusExperiment, ...]:
    raw_experiments = layout.get("experiments")
    experiments: list[CorpusExperiment] = []
    if raw_experiments is None:
        task = str(layout["task"])
        extension = str(layout["extension"])
        shared_paths = [str(value) for value in layout["shared_paths"]]
        suffixes = [str(value) for value in layout["recording_suffixes"]]
        prefix = f"sub-{{subject}}/eeg/sub-{{subject}}_task-{task}"
        experiments.append(
            CorpusExperiment(
                task=task,
                template_recipe=(
                    recipe_path.parent / str(payload["template_recipe"])
                ).resolve(),
                paths=tuple(
                    [*shared_paths, *(f"{prefix}{suffix}" for suffix in suffixes)]
                ),
                primary_path=f"{prefix}_eeg{extension}",
                metadata_path=f"{prefix}_eeg.json",
            )
        )
    else:
        if not isinstance(raw_experiments, list) or not raw_experiments:
            raise CorpusPlanError("layout.experiments must be a non-empty list")
        shared_paths = [str(value) for value in layout.get("shared_paths", [])]
        for index, value in enumerate(raw_experiments):
            if not isinstance(value, dict):
                raise CorpusPlanError(f"layout.experiments[{index}] must be an object")
            task = str(value["task"])
            paths = [*shared_paths, *(str(path) for path in value["paths"])]
            experiments.append(
                CorpusExperiment(
                    task=task,
                    template_recipe=(
                        recipe_path.parent / str(value["template_recipe"])
                    ).resolve(),
                    paths=tuple(paths),
                    primary_path=str(value["primary_path"]),
                    metadata_path=str(value["metadata_path"]),
                )
            )
    tasks = [experiment.task for experiment in experiments]
    if len(set(tasks)) != len(tasks):
        raise CorpusPlanError("Corpus experiment task names must be unique")
    for experiment in experiments:
        if not experiment.template_recipe.is_file():
            raise FileNotFoundError(experiment.template_recipe)
        for path in (
            *experiment.paths,
            experiment.primary_path,
            experiment.metadata_path,
        ):
            _render_path(path, "001", experiment.task)
    return tuple(experiments)


def _render_path(template: str, subject: str, task: str) -> str:
    try:
        rendered = template.format(subject=subject, task=task)
    except (KeyError, ValueError) as error:
        raise CorpusPlanError(f"Invalid corpus path template {template!r}") from error
    path = Path(rendered)
    if path.is_absolute() or ".." in path.parts:
        raise CorpusPlanError(f"Corpus path must stay inside the snapshot: {rendered}")
    return path.as_posix()


def _object(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CorpusPlanError(f"{key} must be an object")
    return value


def _hex_digest(value: str, length: int) -> bool:
    return len(value) == length and all(
        character in "0123456789abcdef" for character in value
    )
