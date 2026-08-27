from __future__ import annotations

import json
from pathlib import Path

import mne
import numpy as np

from neurodata_cnd.source import sha256_file


def synthetic_raw() -> mne.io.RawArray:
    sfreq = 100.0
    times = np.arange(500) / sfreq
    data = np.vstack(
        (
            2e-6 * np.sin(2 * np.pi * 10 * times),
            1e-6 * np.cos(2 * np.pi * 6 * times),
        )
    )
    info = mne.create_info(["Fz", "Cz"], sfreq, ch_types="eeg")
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage("standard_1020", verbose="ERROR")
    raw.set_annotations(
        mne.Annotations(
            onset=[0.5, 2.0, 3.5],
            duration=[0.0, 0.0, 0.0],
            description=["A", "B", "A"],
        )
    )
    return raw


def write_test_recipe(
    path: Path,
    source_path: Path,
    *,
    reader: str = "fif",
    mat_version: str = "5",
) -> Path:
    payload = {
        "recipe_id": "synthetic-cnd-events",
        "recipe_version": f"test-{mat_version.replace('.', '')}",
        "status": "active",
        "source": {
            "dataset_id": "synthetic",
            "provider": "test",
            "url": "https://example.test/dataset",
            "version": "1.0.0",
            "file_url": "https://example.test/source.fif",
            "filename": source_path.name,
            "sha256": sha256_file(source_path),
            "require_pinned_version_before_conversion": True,
        },
        "selection": {
            "modality": "eeg",
            "subject": "001",
            "reader": reader,
            "device_name": "synthetic",
        },
        "trials": {
            "unit": "recording_run",
            "condition_name": "synthetic_condition",
        },
        "features": [
            {
                "name": "a_onset",
                "kind": "annotation_impulse",
                "source_annotation": "A",
                "unit": "binary",
            },
            {
                "name": "b_onset",
                "kind": "annotation_impulse",
                "source_annotation": "B",
                "unit": "binary",
            },
        ],
        "synchronization": {"event_source": "annotations"},
        "output": {
            "format": "CND 1.0",
            "mat_version": mat_version,
            "neural_unit": "V",
        },
        "validation": {"require_round_trip_sample": True},
        "license": {"neural_data": "synthetic test data"},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
