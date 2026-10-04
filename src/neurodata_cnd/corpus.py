"""Run resumable recording jobs; re-export the corpus planning API."""

from __future__ import annotations

import hashlib
import traceback
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

from ._storage import _now, _read_json, _write_json
from .corpus_index import _rebuild_indexes
from .planning import (
    CorpusExperiment,
    CorpusPlanError,
    CorpusRecipe,
    load_corpus_recipe,
    plan_corpus,
)
from .recipe import ConversionRecipe, SourceFileSpec, load_recipe
from .source import remove_cached_source_files

__all__ = [
    "CorpusExperiment",
    "CorpusPlanError",
    "CorpusRecipe",
    "load_corpus_recipe",
    "plan_corpus",
    "run_batch",
    "corpus_status",
]


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
    corpus_root = _corpus_root(plan, output_root)
    jobs = _select_jobs(plan, corpus_root, recording_ids, pilot, retry_failed)
    (corpus_root / "state").mkdir(parents=True, exist_ok=True)
    outcomes: Counter[str] = Counter()
    consecutive_transient_failures = 0
    for job in jobs:
        outcome, transient = _run_job(
            plan, job, corpus_root, cache_root, output_root, cleanup_source
        )
        outcomes[outcome] += 1
        if transient is not None:
            consecutive_transient_failures = (
                consecutive_transient_failures + 1 if transient else 0
            )
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
        status="active",
        source=source,
        selection=selection,
        output=output,
    )


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


def _corpus_root(plan: dict[str, Any], output_root: str | Path) -> Path:
    return (
        Path(output_root).expanduser().resolve()
        / str(plan["corpus_id"])
        / str(plan["corpus_version"])
    )


def _select_jobs(
    plan: dict[str, Any],
    corpus_root: Path,
    recording_ids: set[str] | None,
    pilot: bool,
    retry_failed: bool,
) -> list[dict[str, Any]]:
    """Resolve pilot/retry selection and reject unknown recording IDs."""
    jobs = list(plan["jobs"])
    if pilot:
        recording_ids = set(str(value) for value in plan["pilot_recording_ids"])
    if retry_failed:
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

    return jobs


def _run_job(
    plan: dict[str, Any],
    job: dict[str, Any],
    corpus_root: Path,
    cache_root: str | Path,
    output_root: str | Path,
    cleanup_source: bool,
) -> tuple[str, bool | None]:
    """Resume or execute one job and persist its outcome; None keeps retry history."""
    state_path = corpus_root / "state" / f"{job['recording_id']}.json"
    destination = corpus_root / "recordings" / str(job["recording_id"])
    manifest_path = destination / "manifest.json"
    previous = _read_json(state_path) if state_path.is_file() else {}
    if manifest_path.is_file():
        manifest = _read_json(manifest_path)
        if manifest.get("status") == "validated-local-build":
            _write_state_complete(state_path, job, manifest, previous)
            return "skipped_complete", None
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
        return "completed", False
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
        return "failed", isinstance(
            error, (TimeoutError, urllib.error.URLError, ConnectionError)
        )
