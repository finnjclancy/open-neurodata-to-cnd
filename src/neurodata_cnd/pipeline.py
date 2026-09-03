"""Convert one recording, check it, write a manifest."""

from __future__ import annotations

import json
import platform
import shutil
import tempfile
from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal, cast

import mne
import numpy as np
from cnd_mne import (
    CNDStimulus,
    from_mne,
    read_cnd,
    to_mne,
    validate_cnd,
    write_cnd,
)

from .features import annotation_impulses, bids_event_impulses
from .readers import read_raw
from .recipe import ConversionRecipe, load_recipe
from .source import SourceSnapshot, acquire_source, sha256_file


@dataclass(slots=True, frozen=True)
class ConversionResult:
    output_directory: Path
    neural_path: Path
    stimulus_path: Path
    manifest_path: Path
    source_path: Path
    source_reused_cache: bool
    n_channels: int
    n_samples: int
    n_features: int
    event_counts: dict[str, int]


def convert_recipe(
    recipe: str | Path | ConversionRecipe,
    *,
    cache_root: str | Path,
    output_root: str | Path,
    source_override: str | Path | None = None,
    overwrite: bool = False,
    destination: str | Path | None = None,
) -> ConversionResult:
    """Execute one pinned single-recording recipe and verify its CND round trip."""
    resolved_recipe = (
        load_recipe(recipe) if not isinstance(recipe, ConversionRecipe) else recipe
    )
    snapshot = acquire_source(
        resolved_recipe.source, cache_root, source_override=source_override
    )
    raw = read_raw(snapshot.path, resolved_recipe.selection, source_root=snapshot.root)
    extracted = _extract_features(raw, resolved_recipe, snapshot)
    expected_sfreq = resolved_recipe.synchronization.get("target_sampling_rate_hz")
    if expected_sfreq is not None and not np.isclose(
        float(expected_sfreq), float(raw.info["sfreq"]), rtol=0, atol=1e-12
    ):
        raise ValueError(
            "Source sampling frequency does not match the reviewed recipe: "
            f"expected {float(expected_sfreq):g} Hz, "
            f"observed {float(raw.info['sfreq']):g} Hz"
        )
    maximum_error_samples = resolved_recipe.validation.get(
        "max_event_quantization_error_samples"
    )
    if maximum_error_samples is not None:
        observed_error_samples = extracted.max_quantization_error_seconds * float(
            raw.info["sfreq"]
        )
        if observed_error_samples > float(maximum_error_samples) + 1e-12:
            raise ValueError(
                "Event quantization exceeds the reviewed recipe limit: "
                f"{observed_error_samples:g} samples"
            )
    stimulus = CNDStimulus(
        names=extracted.names,
        features=tuple((array,) for array in extracted.arrays),
        sfreq=float(raw.info["sfreq"]),
        stimulus_indices=(1,),
        condition_indices=(1,),
        condition_names=(str(resolved_recipe.trials["condition_name"]),),
        cnd_version=1.0,
    )
    recording = from_mne(
        raw,
        stimulus=stimulus,
        output_unit=str(resolved_recipe.output.get("neural_unit", "V")),
        device_name=_device_name(raw, resolved_recipe),
        cnd_version=1.0,
        on_unsupported_metadata="ignore",
    )
    if recording.neural is None:
        raise RuntimeError("MNE conversion did not produce CND neural data")
    strict_report = validate_cnd(recording, strict_spec=True)
    strict_report.raise_for_errors()

    resolved_destination = (
        Path(destination).expanduser().resolve()
        if destination is not None
        else Path(output_root).expanduser().resolve()
        / resolved_recipe.source.dataset_id
        / resolved_recipe.recipe_version
    )
    staging = _new_staging_directory(resolved_destination)
    try:
        mat_version = cast(
            Literal["5", "7.3"], str(resolved_recipe.output.get("mat_version", "5"))
        )
        paths = write_cnd(
            recording,
            staging / "dataCND",
            subject=str(resolved_recipe.selection["subject"]),
            mat_version=mat_version,
        )
        if paths.neural is None or paths.stimulus is None:
            raise RuntimeError(
                "The EEG event profile must produce neural and stimulus files"
            )

        round_trip = read_cnd(paths.neural, stimulus_path=paths.stimulus)
        if round_trip.stimulus is None:
            raise RuntimeError("CND read-back did not contain stimulus data")
        round_trip_report = validate_cnd(round_trip, strict_spec=True)
        round_trip_report.raise_for_errors()
        mne_round_trip = to_mne(round_trip, neural_unit=recording.neural.data_unit)
        if len(mne_round_trip.raws) != 1:
            raise RuntimeError("Expected exactly one round-trip CND trial")
        if not np.allclose(
            mne_round_trip.raws[0].get_data(), raw.get_data(), rtol=1e-7, atol=1e-12
        ):
            raise RuntimeError("CND-to-MNE numerical round trip changed the EEG values")
        for name, expected in zip(extracted.names, extracted.arrays, strict=True):
            observed = np.asarray(round_trip.stimulus.feature(name)[0]).squeeze()
            if not np.array_equal(observed, expected):
                raise RuntimeError(f"CND round trip changed stimulus feature {name!r}")

        manifest = _manifest(
            resolved_recipe,
            snapshot,
            raw,
            extracted.event_counts,
            extracted.max_quantization_error_seconds,
            paths.neural,
            paths.stimulus,
            strict_report,
            round_trip_report,
            _content_sha256(round_trip),
        )
        _write_json_atomic(staging / "manifest.json", manifest, overwrite=False)
        _publish_staging(staging, resolved_destination, overwrite=overwrite)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    neural_path = resolved_destination / "dataCND" / paths.neural.name
    stimulus_path = resolved_destination / "dataCND" / paths.stimulus.name
    manifest_path = resolved_destination / "manifest.json"
    return ConversionResult(
        output_directory=resolved_destination,
        neural_path=neural_path,
        stimulus_path=stimulus_path,
        manifest_path=manifest_path,
        source_path=snapshot.path,
        source_reused_cache=snapshot.reused_cache,
        n_channels=len(raw.ch_names),
        n_samples=int(raw.n_times),
        n_features=len(extracted.names),
        event_counts=extracted.event_counts,
    )


def _device_name(raw: mne.io.BaseRaw, recipe: ConversionRecipe) -> str:
    explicit = recipe.selection.get("device_name")
    if explicit:
        return str(explicit)
    return str(raw.info.get("device_info") or raw.info.get("description") or "unknown")


def _extract_features(
    raw: mne.io.BaseRaw, recipe: ConversionRecipe, snapshot: SourceSnapshot
) -> Any:
    kinds = {feature.kind for feature in recipe.features}
    if kinds == {"annotation_impulse"}:
        return annotation_impulses(raw, recipe.features)
    if kinds == {"bids_event_impulse"}:
        relative_path = recipe.selection.get("events_path")
        if not relative_path:
            raise ValueError("BIDS event features require selection.events_path")
        events_path = snapshot.root / str(relative_path)
        if not events_path.is_file():
            raise FileNotFoundError(events_path)
        return bids_event_impulses(
            raw,
            events_path,
            recipe.features,
            sample_index_origin=int(
                recipe.synchronization.get("sample_index_origin", 0)
            ),
        )
    raise ValueError("A recipe must use one supported feature-adapter kind")


def _manifest(
    recipe: ConversionRecipe,
    snapshot: SourceSnapshot,
    raw: mne.io.BaseRaw,
    event_counts: dict[str, int],
    max_quantization_error_seconds: float,
    neural_path: Path,
    stimulus_path: Path,
    strict_report: Any,
    round_trip_report: Any,
    content_sha256: str,
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
                    "name": feature.name,
                    "kind": feature.kind,
                    "source_annotation": feature.source_annotation,
                    "source_column": feature.source_column,
                    "source_value": feature.source_value,
                    "source_values": (
                        list(feature.source_values)
                        if feature.source_values is not None
                        else None
                    ),
                }
                for feature in recipe.features
            ],
            "synchronization": dict(recipe.synchronization),
            "trial_policy": recipe.trials["unit"],
            "neural_unit": recipe.output.get("neural_unit", "V"),
        },
        "contents": {
            "modality": "eeg",
            "subjects": 1,
            "trials": 1,
            "channels": len(raw.ch_names),
            "samples": int(raw.n_times),
            "sampling_frequency_hz": float(raw.info["sfreq"]),
            "duration_seconds": duration,
            "features": [feature.name for feature in recipe.features],
            "event_counts": event_counts,
            "files": output_files,
            "canonical_content_sha256": content_sha256,
        },
        "validation": {
            "strict_cnd": "pass",
            "cnd_to_mne": "pass",
            "source_reconciliation": "pass",
            "max_event_quantization_error_seconds": max_quantization_error_seconds,
            "strict_warnings": [asdict(issue) for issue in strict_report.warnings],
            "round_trip_warnings": [
                asdict(issue) for issue in round_trip_report.warnings
            ],
        },
        "licenses": dict(recipe.license),
    }


def _content_sha256(recording: Any) -> str:
    """Hash scientific content independently of MAT-file header timestamps."""
    neural = recording.neural
    stimulus = recording.stimulus
    if neural is None or stimulus is None:
        raise RuntimeError("The EEG event profile requires paired CND data")
    metadata = {
        "neural_sfreq": neural.sfreq,
        "neural_unit": neural.data_unit,
        "channel_names": neural.channel_names,
        "stimulus_sfreq": stimulus.sfreq,
        "stimulus_names": stimulus.names,
        "stimulus_indices": stimulus.stimulus_indices,
        "condition_indices": stimulus.condition_indices,
        "condition_names": stimulus.condition_names,
    }
    digest = sha256(json.dumps(metadata, sort_keys=True).encode("utf-8"))
    for trial in neural.trials:
        _update_array_digest(digest, np.asarray(trial))
    for feature in stimulus.features:
        for trial in feature:
            _update_array_digest(digest, np.asarray(trial))
    return digest.hexdigest()


def _update_array_digest(digest: Any, array: np.ndarray) -> None:
    normalized = np.ascontiguousarray(array, dtype="<f8")
    digest.update(json.dumps(normalized.shape).encode("ascii"))
    digest.update(normalized.tobytes(order="C"))


def _new_staging_directory(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent)
    )


def _publish_staging(staging: Path, destination: Path, *, overwrite: bool) -> None:
    if not destination.exists():
        staging.rename(destination)
        return
    if not overwrite:
        raise FileExistsError(f"Refusing to overwrite {destination}")
    backup = destination.with_name(f".{destination.name}.backup")
    if backup.exists():
        raise FileExistsError(f"Cannot replace release while backup exists: {backup}")
    destination.rename(backup)
    try:
        staging.rename(destination)
    except BaseException:
        backup.rename(destination)
        raise
    else:
        shutil.rmtree(backup)


def _write_json_atomic(path: Path, payload: dict[str, Any], *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
