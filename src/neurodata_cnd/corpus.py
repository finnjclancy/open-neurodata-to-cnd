"""Planning and resumable execution for checksum-pinned CND corpora."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import traceback
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .recipe import ConversionRecipe, SourceFileSpec, load_recipe
from .source import remove_cached_source_files


class CorpusPlanError(ValueError):
    """A corpus recipe or remote inventory is incomplete or inconsistent."""


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


def plan_corpus(
    recipe_path: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create an immutable per-recording plan from a pinned remote manifest."""
    recipe = load_corpus_recipe(recipe_path)
    inventory_bytes = _fetch(recipe.inventory_url)
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
    if observed != recipe.inventory_sha256:
        raise CorpusPlanError(
            "Remote inventory checksum changed: "
            f"expected {recipe.inventory_sha256}, observed {observed}"
        )
    by_path = {str(entry["path"]): entry for entry in entries}
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


def run_batch(
    plan_path: str | Path,
    *,
    cache_root: str | Path,
    output_root: str | Path,
    recording_ids: set[str] | None = None,
    pilot: bool = False,
    cleanup_source: bool = True,
    retry_failed: bool = False,
) -> dict[str, Any]:
    """Run independent corpus jobs sequentially and continue after failures."""
    resolved_plan_path = Path(plan_path).expanduser().resolve()
    plan = _read_json(resolved_plan_path)
    plan["_plan_directory"] = str(resolved_plan_path.parent)
    jobs = list(plan["jobs"])
    if pilot:
        recording_ids = set(str(value) for value in plan["pilot_recording_ids"])
    if retry_failed:
        corpus_root = _corpus_root(plan, output_root)
        failed = {
            path.stem
            for path in (corpus_root / "state").glob("*.json")
            if _read_json(path).get("status") == "failed"
        }
        recording_ids = failed
    if recording_ids is not None:
        unknown = recording_ids - {str(job["recording_id"]) for job in jobs}
        if unknown:
            raise CorpusPlanError(f"Unknown recording IDs: {sorted(unknown)}")
        jobs = [job for job in jobs if job["recording_id"] in recording_ids]

    corpus_root = _corpus_root(plan, output_root)
    (corpus_root / "state").mkdir(parents=True, exist_ok=True)
    outcomes: Counter[str] = Counter()
    consecutive_transient_failures = 0
    for job in jobs:
        state_path = corpus_root / "state" / f"{job['recording_id']}.json"
        destination = corpus_root / "recordings" / str(job["recording_id"])
        manifest_path = destination / "manifest.json"
        previous = _read_json(state_path) if state_path.is_file() else {}
        if manifest_path.is_file():
            manifest = _read_json(manifest_path)
            if manifest.get("status") == "validated-local-build":
                _write_state_complete(state_path, job, manifest, previous)
                outcomes["skipped_complete"] += 1
                _rebuild_indexes(plan, corpus_root)
                continue
        if previous.get("status") == "complete":
            raise RuntimeError(
                f"State says {job['recording_id']} is complete but manifest is absent"
            )

        attempt = int(previous.get("attempt", 0)) + 1
        _write_json(
            state_path,
            {
                "recording_id": job["recording_id"],
                "status": "running",
                "attempt": attempt,
                "started_at": _now(),
            },
            overwrite=True,
        )
        try:
            conversion_recipe = _job_recipe(plan, job)
            result = _convert_recording(
                conversion_recipe,
                cache_root=cache_root,
                output_root=output_root,
                destination=destination,
            )
            manifest = _read_json(result.manifest_path)
            expected = job["expected"]
            if result.n_channels != int(expected["channels"]):
                raise RuntimeError("Converted channel count differs from the plan")
            if result.n_samples != round(
                float(expected["duration_seconds"])
                * float(expected["sampling_frequency_hz"])
            ):
                raise RuntimeError("Converted sample count differs from the plan")
            cleaned = 0
            if cleanup_source:
                subject_paths = {
                    str(file["path"])
                    for file in job["files"]
                    if str(file["path"]).startswith(f"sub-{job['subject']}/")
                }
                cleaned = remove_cached_source_files(
                    conversion_recipe.source, cache_root, subject_paths
                )
            _write_state_complete(
                state_path,
                job,
                manifest,
                {"attempt": attempt, "source_files_removed": cleaned},
            )
            outcomes["completed"] += 1
            consecutive_transient_failures = 0
        except Exception as error:
            _write_json(
                state_path,
                {
                    "recording_id": job["recording_id"],
                    "status": "failed",
                    "attempt": attempt,
                    "failed_at": _now(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                },
                overwrite=True,
            )
            outcomes["failed"] += 1
            if isinstance(
                error, (TimeoutError, urllib.error.URLError, ConnectionError)
            ):
                consecutive_transient_failures += 1
            else:
                consecutive_transient_failures = 0
        _rebuild_indexes(plan, corpus_root)
        if consecutive_transient_failures >= 3:
            outcomes["stopped_after_transient_failures"] += 1
            break
    summary = _rebuild_indexes(plan, corpus_root)
    return {
        "corpus_directory": str(corpus_root),
        "selected_jobs": len(jobs),
        "outcomes": dict(outcomes),
        "summary": summary,
    }


def corpus_status(corpus_directory: str | Path) -> dict[str, Any]:
    """Read the current corpus summary without changing state."""
    path = Path(corpus_directory).expanduser().resolve() / "summary.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return _read_json(path)


def _convert_recording(*args: Any, **kwargs: Any) -> Any:
    """Import the conversion stack only when a batch job actually runs."""
    from .pipeline import convert_recipe

    return convert_recipe(*args, **kwargs)


def _job_recipe(plan: dict[str, Any], job: dict[str, Any]) -> ConversionRecipe:
    template_value = job.get("template_recipe", plan.get("template_recipe"))
    template_digest = job.get(
        "template_recipe_sha256", plan.get("template_recipe_sha256")
    )
    if template_value is None or template_digest is None:
        raise CorpusPlanError(f"Job {job['recording_id']} has no pinned template")
    template = Path(str(plan["_plan_directory"])) / str(template_value)
    observed_template_digest = hashlib.sha256(template.read_bytes()).hexdigest()
    if observed_template_digest != str(template_digest):
        raise CorpusPlanError(
            "Template recipe changed after corpus planning; create a new plan/version"
        )
    base = load_recipe(template)
    source_payload = plan["source"]
    files = tuple(
        SourceFileSpec(
            path=str(item["path"]),
            url=str(item["url"]),
            sha256=(
                str(item["checksum"])
                if item["checksum_algorithm"] == "sha256"
                else None
            ),
            checksum_algorithm=str(item["checksum_algorithm"]),
            checksum=str(item["checksum"]),
        )
        for item in job["files"]
    )
    source = replace(
        base.source,
        dataset_id=str(source_payload["dataset_id"]),
        provider=str(source_payload["provider"]),
        url=str(source_payload["url"]),
        version=str(source_payload["version"]),
        doi=source_payload.get("doi"),
        files=files,
        primary_path=str(job["primary_path"]),
    )
    selection = dict(base.selection)
    selection["subject"] = str(job["subject"])
    selection["task"] = str(job["task"])
    event_paths = [
        str(item["path"])
        for item in job["files"]
        if str(item["path"]).endswith("_events.tsv")
    ]
    if event_paths:
        if len(event_paths) != 1:
            raise CorpusPlanError(
                f"Expected one events table for {job['recording_id']}"
            )
        selection["events_path"] = event_paths[0]
    if selection.get("channel_type_policy") == "all_eeg":
        selection["channel_type_evidence"] = (
            f"BIDS sidecar declares EEGChannelCount={job['expected']['channels']}; "
            "the source channels table records channel type as n/a."
        )
    output = dict(base.output)
    output["release_id"] = (
        f"{plan['corpus_id']}/{plan['corpus_version']}/{job['recording_id']}"
    )
    return replace(
        base,
        recipe_id=f"{base.recipe_id}:{job['recording_id']}",
        recipe_version=str(plan["corpus_version"]),
        source=source,
        selection=selection,
        output=output,
    )


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


def _render_path(template: str, subject: str, task: str) -> str:
    try:
        rendered = template.format(subject=subject, task=task)
    except (KeyError, ValueError) as error:
        raise CorpusPlanError(f"Invalid corpus path template {template!r}") from error
    path = Path(rendered)
    if path.is_absolute() or ".." in path.parts:
        raise CorpusPlanError(f"Corpus path must stay inside the snapshot: {rendered}")
    return path.as_posix()


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


def _write_state_complete(
    path: Path,
    job: dict[str, Any],
    manifest: dict[str, Any],
    previous: dict[str, Any],
) -> None:
    _write_json(
        path,
        {
            "recording_id": job["recording_id"],
            "status": "complete",
            "attempt": int(previous.get("attempt", 1)),
            "completed_at": previous.get("completed_at", _now()),
            "source_files_removed": int(previous.get("source_files_removed", 0)),
            "manifest": f"recordings/{job['recording_id']}/manifest.json",
            "canonical_content_sha256": manifest["contents"][
                "canonical_content_sha256"
            ],
        },
        overwrite=True,
    )


def _rebuild_indexes(plan: dict[str, Any], corpus_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for job in plan["jobs"]:
        state_path = corpus_root / "state" / f"{job['recording_id']}.json"
        state = (
            _read_json(state_path) if state_path.is_file() else {"status": "pending"}
        )
        row: dict[str, Any] = {
            "recording_id": job["recording_id"],
            "subject": job["subject"],
            "task": job["task"],
            "group": job["participant"].get("GROUP"),
            "status": state["status"],
            "attempt": int(state.get("attempt", 0)),
            "expected_channels": job["expected"]["channels"],
            "expected_duration_seconds": job["expected"]["duration_seconds"],
            "source_bytes": job["source_bytes"],
        }
        manifest_path = (
            corpus_root / "recordings" / str(job["recording_id"]) / "manifest.json"
        )
        if manifest_path.is_file():
            manifest = _read_json(manifest_path)
            contents = manifest["contents"]
            row.update(
                {
                    "channels": contents["channels"],
                    "samples": contents["samples"],
                    "sampling_frequency_hz": contents["sampling_frequency_hz"],
                    "duration_seconds": contents["duration_seconds"],
                    "event_counts": contents["event_counts"],
                    "canonical_content_sha256": contents["canonical_content_sha256"],
                    "output_bytes": sum(
                        int(file["size_bytes"]) for file in contents["files"]
                    ),
                    "manifest": f"recordings/{job['recording_id']}/manifest.json",
                }
            )
        if state.get("error"):
            row["error_type"] = state.get("error_type")
            row["error"] = state["error"]
        rows.append(row)
    index_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    _write_text(corpus_root / "index.jsonl", index_text)
    statuses = Counter(str(row["status"]) for row in rows)
    complete_rows = [row for row in rows if row["status"] == "complete"]
    event_counts: Counter[str] = Counter()
    for row in complete_rows:
        event_counts.update(
            {key: int(value) for key, value in row.get("event_counts", {}).items()}
        )
    channel_counts = Counter(str(row["channels"]) for row in complete_rows)
    group_counts = Counter(
        str(row["group"]) for row in complete_rows if row["group"] is not None
    )
    task_counts = Counter(str(row["task"]) for row in complete_rows)
    summary = {
        "corpus_id": plan["corpus_id"],
        "corpus_version": plan["corpus_version"],
        "release_status": (
            "complete" if len(complete_rows) == len(rows) else "in_progress"
        ),
        "updated_at": _now(),
        "recordings": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "completed_samples": sum(int(row.get("samples", 0)) for row in complete_rows),
        "completed_duration_seconds": sum(
            float(row.get("duration_seconds", 0)) for row in complete_rows
        ),
        "completed_source_bytes": sum(
            int(row["source_bytes"]) for row in complete_rows
        ),
        "completed_output_bytes": sum(
            int(row.get("output_bytes", 0)) for row in complete_rows
        ),
        "event_counts": dict(sorted(event_counts.items())),
        "channel_count_distribution": dict(sorted(channel_counts.items())),
        "group_distribution": dict(sorted(group_counts.items())),
        "task_distribution": dict(sorted(task_counts.items())),
        "completed_canonical_content_sha256": _corpus_content_digest(complete_rows),
        "failed_recording_ids": [
            row["recording_id"] for row in rows if row["status"] == "failed"
        ],
    }
    _write_json(corpus_root / "summary.json", summary, overwrite=True)
    return summary


def _corpus_root(plan: dict[str, Any], output_root: str | Path) -> Path:
    return (
        Path(output_root).expanduser().resolve()
        / str(plan["corpus_id"])
        / str(plan["corpus_version"])
    )


def _corpus_content_digest(rows: list[dict[str, Any]]) -> str:
    """Hash ordered recording identities and canonical scientific digests."""
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item["recording_id"])):
        digest.update(str(row["recording_id"]).encode())
        digest.update(b"\0")
        digest.update(str(row["canonical_content_sha256"]).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _entry(by_path: dict[str, dict[str, Any]], path: str) -> dict[str, Any]:
    try:
        return by_path[path]
    except KeyError as error:
        raise CorpusPlanError(f"Required source file is absent: {path}") from error


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "open-neurodata-to-cnd/0.2"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CorpusPlanError(f"Expected a JSON object: {path}")
    return value


def _object(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CorpusPlanError(f"{key} must be an object")
    return value


def _hex_digest(value: str, length: int) -> bool:
    return len(value) == length and all(
        character in "0123456789abcdef" for character in value
    )


def _write_json(path: Path, value: dict[str, Any], *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    _write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _now() -> str:
    return datetime.now(UTC).isoformat()
