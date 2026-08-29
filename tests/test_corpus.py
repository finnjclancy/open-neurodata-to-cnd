from __future__ import annotations

import hashlib
import json
import urllib.error
from pathlib import Path
from types import SimpleNamespace

from conftest import synthetic_raw, write_test_recipe

from neurodata_cnd import corpus


def _job(recording_id: str, channels: int, duration: float, group: str) -> dict:
    subject = recording_id.removeprefix("sub-")
    return {
        "recording_id": recording_id,
        "subject": subject,
        "task": "Oddball",
        "primary_path": f"sub-{subject}/eeg/sub-{subject}_task-Oddball_eeg.set",
        "source_bytes": 100,
        "expected": {
            "channels": channels,
            "sampling_frequency_hz": 100.0,
            "duration_seconds": duration,
        },
        "participant": {"GROUP": group},
        "files": [
            {
                "path": f"sub-{subject}/eeg/sub-{subject}_task-Oddball_eeg.set",
                "url": "https://example.test/source.set",
                "size_bytes": 100,
                "checksum_algorithm": "sha256",
                "checksum": "0" * 64,
            }
        ],
    }


def test_pilot_selection_covers_channel_layouts_groups_and_extremes() -> None:
    jobs = [
        _job("sub-001", 63, 8.0, "PD"),
        _job("sub-002", 64, 7.0, "PD"),
        _job("sub-003", 66, 6.0, "PD"),
        _job("sub-004", 63, 2.0, "Control"),
        _job("sub-005", 63, 14.0, "PD"),
    ]

    selected = corpus._select_pilot(jobs, count=5)

    assert set(selected) == {job["recording_id"] for job in jobs}


def test_batch_is_resumable_and_builds_index(tmp_path: Path, monkeypatch) -> None:
    raw = synthetic_raw()
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    template = write_test_recipe(tmp_path / "template.json", source)
    job = _job("sub-001", 2, 5.0, "Control")
    plan = {
        "plan_version": "1.0.0",
        "corpus_id": "example",
        "corpus_version": "0.2.0",
        "template_recipe": template.name,
        "template_recipe_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        "source": {
            "dataset_id": "example",
            "provider": "fixture",
            "version": "1.0.0",
            "url": "https://example.test/dataset",
            "doi": None,
        },
        "shared_paths": [],
        "pilot_recording_ids": ["sub-001"],
        "jobs": [job],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    calls = 0

    def fake_convert(*args, destination: Path, **kwargs):
        nonlocal calls
        calls += 1
        destination.mkdir(parents=True)
        manifest_path = destination / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "validated-local-build",
                    "contents": {
                        "channels": 2,
                        "samples": 500,
                        "sampling_frequency_hz": 100.0,
                        "duration_seconds": 5.0,
                        "event_counts": {"a_onset": 2, "b_onset": 1},
                        "files": [{"size_bytes": 1000}],
                        "canonical_content_sha256": "a" * 64,
                    },
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(manifest_path=manifest_path, n_channels=2, n_samples=500)

    monkeypatch.setattr(corpus, "_convert_recording", fake_convert)
    options = {
        "cache_root": tmp_path / "cache",
        "output_root": tmp_path / "outputs",
        "cleanup_source": False,
    }
    first = corpus.run_batch(plan_path, **options)
    second = corpus.run_batch(plan_path, **options)

    assert first["outcomes"] == {"completed": 1}
    assert second["outcomes"] == {"skipped_complete": 1}
    assert calls == 1
    summary = second["summary"]
    assert summary["status_counts"] == {"complete": 1}
    assert summary["release_status"] == "complete"
    assert len(summary["completed_canonical_content_sha256"]) == 64
    index = (tmp_path / "outputs" / "example" / "0.2.0" / "index.jsonl").read_text(
        encoding="utf-8"
    )
    assert json.loads(index)["canonical_content_sha256"] == "a" * 64


def test_batch_stops_after_three_transient_network_failures(
    tmp_path: Path, monkeypatch
) -> None:
    raw = synthetic_raw()
    source = tmp_path / "source_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")
    template = write_test_recipe(tmp_path / "template.json", source)
    jobs = [_job(f"sub-{index:03d}", 2, 5.0, "Control") for index in range(1, 6)]
    plan = {
        "plan_version": "1.0.0",
        "corpus_id": "example",
        "corpus_version": "0.2.0",
        "template_recipe": template.name,
        "template_recipe_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        "source": {
            "dataset_id": "example",
            "provider": "fixture",
            "version": "1.0.0",
            "url": "https://example.test/dataset",
            "doi": None,
        },
        "shared_paths": [],
        "pilot_recording_ids": [],
        "jobs": jobs,
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    calls = 0

    def fail_transiently(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise urllib.error.URLError("temporary DNS failure")

    monkeypatch.setattr(corpus, "_convert_recording", fail_transiently)
    result = corpus.run_batch(
        plan_path,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
        cleanup_source=False,
    )

    assert calls == 3
    assert result["outcomes"] == {
        "failed": 3,
        "stopped_after_transient_failures": 1,
    }
    assert result["summary"]["status_counts"] == {"failed": 3, "pending": 2}
