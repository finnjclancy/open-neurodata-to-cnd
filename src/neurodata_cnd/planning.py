"""Turn a pinned dataset inventory into independent recording jobs."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ._storage import _now, _write_json
from .corpus_recipe import (
    CorpusExperiment as CorpusExperiment,
)
from .corpus_recipe import (
    CorpusRecipe as CorpusRecipe,
)
from .corpus_recipe import (
    _render_path,
)
from .corpus_recipe import (
    load_corpus_recipe as load_corpus_recipe,
)
from .recipe import CorpusPlanError as CorpusPlanError
from .source import USER_AGENT


def plan_corpus(
    recipe_path: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create an immutable per-recording plan from a pinned remote manifest."""
    recipe = load_corpus_recipe(recipe_path)
    by_path = _load_inventory(recipe.inventory_url, recipe.inventory_sha256)
    participant_metadata = _participant_metadata(by_path, recipe)
    destination = Path(output_path).expanduser().resolve()

    jobs: list[dict[str, Any]] = []
    discovered = [
        (experiment, _discover_subjects(by_path, experiment))
        for experiment in recipe.experiments
    ]
    multiple_experiments = len(discovered) > 1
    metadata_entries: list[tuple[str, dict[str, Any]]] = []
    for experiment, subjects in discovered:
        for subject in subjects:
            recording_id = _recording_id(subject, experiment.task, multiple_experiments)
            path = _render_path(experiment.metadata_path, subject, experiment.task)
            metadata_entries.append((recording_id, _entry(by_path, path)))
    with ThreadPoolExecutor(max_workers=12) as executor:
        recording_metadata = dict(
            executor.map(
                lambda pair: (pair[0], _fetch_json_entry(pair[1])), metadata_entries
            )
        )

    selected_paths: set[str] = set()
    for experiment, subjects in discovered:
        for subject in subjects:
            recording_id = _recording_id(subject, experiment.task, multiple_experiments)
            paths = [
                _render_path(path, subject, experiment.task)
                for path in experiment.paths
            ]
            file_entries = [_entry(by_path, path) for path in paths]
            primary_path = _render_path(
                experiment.primary_path, subject, experiment.task
            )
            if primary_path not in paths:
                raise CorpusPlanError(
                    f"Primary recording is undeclared for {recording_id}"
                )
            metadata = recording_metadata[recording_id]
            participant = participant_metadata.get(f"sub-{subject}", {})
            selected_paths.update(paths)
            jobs.append(
                {
                    "recording_id": recording_id,
                    "subject": subject,
                    "task": experiment.task,
                    "template_recipe": os.path.relpath(
                        experiment.template_recipe, start=destination.parent
                    ),
                    "template_recipe_sha256": hashlib.sha256(
                        experiment.template_recipe.read_bytes()
                    ).hexdigest(),
                    "primary_path": primary_path,
                    "source_bytes": sum(int(entry["size"]) for entry in file_entries),
                    "expected": {
                        "channels": int(metadata["EEGChannelCount"]),
                        "sampling_frequency_hz": float(metadata["SamplingFrequency"]),
                        "duration_seconds": float(metadata["RecordingDuration"]),
                    },
                    "participant": {
                        key: participant[key]
                        for key in ("GROUP",)
                        if participant.get(key) not in {None, "", "n/a"}
                    },
                    "files": [_plan_file(entry) for entry in file_entries],
                }
            )

    pilot = _select_pilot(jobs, count=max(5, len(recipe.experiments)))
    plan = {
        "plan_version": "1.0.0",
        "corpus_id": recipe.corpus_id,
        "corpus_version": recipe.corpus_version,
        "generated_at": _now(),
        "source": {
            "dataset_id": recipe.dataset_id,
            "provider": recipe.provider,
            "version": recipe.source_version,
            "url": recipe.source_url,
            "doi": recipe.source_doi,
            "inventory_url": recipe.inventory_url,
            "inventory_canonical_sha256": recipe.inventory_sha256,
        },
        "recording_count": len(jobs),
        "source_bytes": sum(int(by_path[path]["size"]) for path in selected_paths),
        "pilot_recording_ids": pilot,
        "jobs": jobs,
    }
    _write_json(destination, plan, overwrite=overwrite)
    return plan


def _discover_subjects(
    by_path: dict[str, dict[str, Any]], experiment: CorpusExperiment
) -> list[str]:
    rendered = experiment.primary_path.replace("{task}", experiment.task)
    pieces = rendered.split("{subject}")
    if len(pieces) < 2:
        raise CorpusPlanError("Experiment primary_path must contain {subject}")
    expression = re.escape(pieces[0]) + r"(?P<subject>[^/]+)"
    expression += "".join(
        re.escape(piece)
        if index == len(pieces) - 1
        else re.escape(piece) + r"(?P=subject)"
        for index, piece in enumerate(pieces[1:], start=1)
    )
    pattern = re.compile(f"^{expression}$")
    subjects = sorted(
        match.group("subject")
        for path in by_path
        if (match := pattern.match(path)) is not None
    )
    if not subjects:
        raise CorpusPlanError(
            f"No recordings match the corpus layout for task {experiment.task}"
        )
    return subjects


def _recording_id(subject: str, task: str, multiple_experiments: bool) -> str:
    if multiple_experiments:
        return f"sub-{subject}_task-{task}"
    return f"sub-{subject}"


def _participant_metadata(
    by_path: dict[str, dict[str, Any]], recipe: CorpusRecipe
) -> dict[str, dict[str, str]]:
    if recipe.participants_path is None:
        return {}
    entry = _entry(by_path, recipe.participants_path)
    content = _fetch_entry(entry).decode("utf-8")
    return {
        str(row["participant_id"]): dict(row)
        for row in csv.DictReader(content.splitlines(), delimiter="\t")
    }


def _fetch_json_entry(entry: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(_fetch_entry(entry))
    if not isinstance(value, dict):
        raise CorpusPlanError(f"Expected a JSON object at {entry['path']}")
    return value


def _fetch_entry(entry: dict[str, Any]) -> bytes:
    content = _fetch(str(entry["bytes_url"]))
    algorithm = str(entry["checksum_algorithm"])
    observed = _checksum_bytes(content, algorithm)
    if observed != str(entry["checksum"]):
        raise CorpusPlanError(f"Checksum mismatch while inspecting {entry['path']}")
    return content


def _checksum_bytes(content: bytes, algorithm: str) -> str:
    if algorithm == "sha256":
        return hashlib.sha256(content).hexdigest()
    if algorithm == "git":
        digest = hashlib.sha1(usedforsecurity=False)
        digest.update(f"blob {len(content)}\0".encode())
        digest.update(content)
        return digest.hexdigest()
    raise CorpusPlanError(f"Unsupported inventory checksum {algorithm!r}")


def _plan_file(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(entry["path"]),
        "url": str(entry["bytes_url"]),
        "size_bytes": int(entry["size"]),
        "checksum_algorithm": str(entry["checksum_algorithm"]),
        "checksum": str(entry["checksum"]),
    }


def _select_pilot(jobs: list[dict[str, Any]], count: int) -> list[str]:
    selected: list[dict[str, Any]] = []
    for task in dict.fromkeys(str(job["task"]) for job in jobs):
        selected.append(next(job for job in jobs if job["task"] == task))
    for channel_count in sorted({job["expected"]["channels"] for job in jobs}):
        job = next(job for job in jobs if job["expected"]["channels"] == channel_count)
        if job not in selected:
            selected.append(job)
    extremes = sorted(jobs, key=lambda job: job["expected"]["duration_seconds"])
    for job in (extremes[0], extremes[-1]):
        if job not in selected:
            selected.append(job)
    groups = {job["participant"].get("GROUP") for job in selected}
    for job in jobs:
        if job["participant"].get("GROUP") not in groups:
            selected.append(job)
            groups.add(job["participant"].get("GROUP"))
    for job in jobs:
        if job not in selected:
            selected.append(job)
        if len(selected) >= count:
            break
    return [str(job["recording_id"]) for job in selected[:count]]


def _entry(by_path: dict[str, dict[str, Any]], path: str) -> dict[str, Any]:
    try:
        return by_path[path]
    except KeyError as error:
        raise CorpusPlanError(f"Required source file is absent: {path}") from error


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _load_inventory(url: str, expected_digest: str) -> dict[str, dict[str, Any]]:
    """Verify the pinned inventory before using any recording entries."""
    inventory_bytes = _fetch(url)
    entries = json.loads(inventory_bytes)
    if not isinstance(entries, list):
        raise CorpusPlanError("Remote inventory must be a JSON array")
    stable_inventory = [
        {
            key: entry[key]
            for key in (
                "path",
                "size",
                "checksum_algorithm",
                "checksum",
                "bytes_url",
            )
        }
        for entry in entries
    ]
    observed = hashlib.sha256(
        json.dumps(stable_inventory, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if observed != expected_digest:
        raise CorpusPlanError(
            "Remote inventory checksum changed: "
            f"expected {expected_digest}, observed {observed}"
        )
    return {str(entry["path"]): entry for entry in entries}
