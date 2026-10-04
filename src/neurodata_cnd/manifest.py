"""Record source provenance, conversion choices, and content hashes."""

from __future__ import annotations

import json
import platform
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any

import mne
import numpy as np
from cnd_mne import CNDRecording, ValidationReport

from .recipe import ConversionRecipe
from .source import SourceSnapshot, sha256_file


def build_manifest(
    recipe: ConversionRecipe,
    snapshot: SourceSnapshot,
    raw: mne.io.BaseRaw,
    event_counts: dict[str, int],
    max_quantization_error_seconds: float,
    neural_path: Path,
    stimulus_path: Path,
    strict_report: ValidationReport,
    round_trip_report: ValidationReport,
    content_sha256: str,
    external_raw: mne.io.BaseRaw | None,
    channel_location_check: str,
) -> dict[str, Any]:
    duration = raw.n_times / float(raw.info["sfreq"])
    primary_record = next(
        item for item in snapshot.files if item["path"] == recipe.source.primary_path
    )
    output_files = []
    for path in (neural_path, stimulus_path):
        output_files.append(
            {
                "path": f"dataCND/{path.name}",
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "manifest_version": "1.0.0",
        "release_id": recipe.output.get(
            "release_id", f"{recipe.source.dataset_id}/{recipe.recipe_version}"
        ),
        "status": "validated-local-build",
        "source": {
            "dataset_id": recipe.source.dataset_id,
            "provider": recipe.source.provider,
            "version": recipe.source.version,
            "doi": recipe.source.doi,
            "url": recipe.source.url,
            "size_bytes": snapshot.size_bytes,
            "sha256": primary_record.get("sha256"),
            "primary_checksum_algorithm": primary_record.get(
                "checksum_algorithm", "sha256"
            ),
            "primary_checksum": primary_record.get(
                "checksum", primary_record.get("sha256")
            ),
            "snapshot_sha256": snapshot.sha256,
            "primary_path": recipe.source.primary_path,
            "files": list(snapshot.files),
        },
        "conversion": {
            "recipe_id": recipe.recipe_id,
            "recipe_version": recipe.recipe_version,
            "software": {
                "open-neurodata-to-cnd": version("open-neurodata-to-cnd"),
                "cnd-mne-converter": version("cnd-mne-converter"),
                "mne": mne.__version__,
                "mne-bids": version("mne-bids"),
                "python": platform.python_version(),
            },
            "reader": recipe.selection.get("reader", "auto"),
            "channel_type_policy": recipe.selection.get(
                "channel_type_policy", "source"
            ),
            "channel_type_evidence": recipe.selection.get("channel_type_evidence"),
            "feature_mappings": [
                {
                    key: list(value) if isinstance(value, tuple) else value
                    for key, value in asdict(feature).items()
                    if key not in {"unit", "description"}
                }
                for feature in recipe.features
            ],
            "synchronization": dict(recipe.synchronization),
            "trial_policy": recipe.trials["unit"],
            "neural_unit": recipe.output.get("neural_unit", "V"),
            "external_unit": recipe.output.get("external_unit"),
        },
        "contents": {
            "modality": "eeg",
            "subjects": 1,
            "trials": 1,
            "channels": len(raw.ch_names),
            "external_channels": (
                len(external_raw.ch_names) if external_raw is not None else 0
            ),
            "external_channel_names": (
                list(external_raw.ch_names) if external_raw is not None else []
            ),
            "external_channel_types": (
                external_raw.get_channel_types() if external_raw is not None else []
            ),
            "samples": int(raw.n_times),
            "sampling_frequency_hz": float(raw.info["sfreq"]),
            "stimulus_sampling_frequency_hz": float(
                recipe.synchronization.get(
                    "stimulus_sampling_rate_hz", raw.info["sfreq"]
                )
            ),
            "duration_seconds": duration,
            "features": [feature.name for feature in recipe.features],
            "event_counts": event_counts,
            "files": output_files,
            "canonical_content_sha256": content_sha256,
        },
        "validation": {
            "strict_cnd": "pass",
            "cnd_to_mne": "pass",
            "external_channels_round_trip": (
                "pass" if external_raw is not None else "not_applicable"
            ),
            "channel_locations_round_trip": channel_location_check,
            "source_reconciliation": "pass",
            "max_event_quantization_error_seconds": max_quantization_error_seconds,
            "strict_warnings": [asdict(issue) for issue in strict_report.warnings],
            "round_trip_warnings": [
                asdict(issue) for issue in round_trip_report.warnings
            ],
        },
        "licenses": dict(recipe.license),
    }


def content_sha256(recording: CNDRecording) -> str:
    """Hash scientific content independently of MAT-file header timestamps."""
    neural = recording.neural
    stimulus = recording.stimulus
    if neural is None or stimulus is None:
        raise RuntimeError("The EEG event profile requires paired CND data")
    metadata = {
        "neural_sfreq": neural.sfreq,
        "neural_unit": neural.data_unit,
        "channel_names": neural.channel_names,
        "external_description": neural.external_description,
        "external_channel_names": (
            np.atleast_1d(neural.external_fields["channelNames"]).tolist()
            if "channelNames" in neural.external_fields
            else None
        ),
        "external_channel_types": (
            np.atleast_1d(neural.external_fields["channelTypes"]).tolist()
            if "channelTypes" in neural.external_fields
            else None
        ),
        "external_unit": neural.external_fields.get("dataUnit"),
        "stimulus_sfreq": stimulus.sfreq,
        "stimulus_names": stimulus.names,
        "stimulus_indices": stimulus.stimulus_indices,
        "condition_indices": stimulus.condition_indices,
        "condition_names": stimulus.condition_names,
    }
    digest = sha256(json.dumps(metadata, sort_keys=True).encode("utf-8"))
    for trial in neural.trials:
        _update_array_digest(digest, np.asarray(trial))
    for trial in neural.external_trials or ():
        _update_array_digest(digest, np.asarray(trial))
    for feature in stimulus.features:
        for trial in feature:
            _update_array_digest(digest, np.asarray(trial))
    return digest.hexdigest()


def _update_array_digest(digest: Any, array: np.ndarray) -> None:
    normalized = np.ascontiguousarray(array, dtype="<f8")
    digest.update(json.dumps(normalized.shape).encode("ascii"))
    digest.update(normalized.tobytes(order="C"))
