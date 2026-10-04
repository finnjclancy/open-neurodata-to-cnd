"""Rebuild corpus indexes and summaries from persisted job state."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ._storage import _now, _read_json, _write_json, _write_text


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


def _corpus_content_digest(rows: list[dict[str, Any]]) -> str:
    """Hash ordered recording identities and canonical scientific digests."""
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item["recording_id"])):
        digest.update(str(row["recording_id"]).encode())
        digest.update(b"\0")
        digest.update(str(row["canonical_content_sha256"]).encode())
        digest.update(b"\n")
    return digest.hexdigest()
