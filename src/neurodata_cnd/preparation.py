"""Build synchronized CND data from a recipe and its source snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mne
import numpy as np
from cnd_mne import CNDRecording, CNDStimulus, ValidationReport, from_mne, validate_cnd

from .features import (
    ExtractedFeatures,
    annotation_impulses,
    audio_envelopes,
    bids_event_impulses,
)
from .readers import read_raw, split_eeg_and_external
from .recipe import ConversionRecipe
from .round_trip import _raise_validation_errors
from .source import SourceSnapshot, acquire_source


def _device_name(raw: mne.io.BaseRaw, recipe: ConversionRecipe) -> str:
    explicit = recipe.selection.get("device_name")
    if explicit:
        return str(explicit)
    return str(raw.info.get("device_info") or raw.info.get("description") or "unknown")


def _extract_features(
    raw: mne.io.BaseRaw, recipe: ConversionRecipe, snapshot: SourceSnapshot
) -> ExtractedFeatures:
    target_sfreq = float(
        recipe.synchronization.get("stimulus_sampling_rate_hz", raw.info["sfreq"])
    )
    names: list[str] = []
    arrays: list[np.ndarray] = []
    counts: dict[str, int] = {}
    maximum_error = 0.0
    for feature in recipe.features:
        if feature.kind == "annotation_impulse":
            extracted = annotation_impulses(raw, (feature,), target_sfreq=target_sfreq)
        elif feature.kind == "bids_event_impulse":
            relative_path = recipe.selection.get("events_path")
            if not relative_path:
                raise ValueError("BIDS event features require selection.events_path")
            events_path = snapshot.root / str(relative_path)
            if not events_path.is_file():
                raise FileNotFoundError(events_path)
            extracted = bids_event_impulses(
                raw,
                events_path,
                (feature,),
                sample_index_origin=int(
                    recipe.synchronization.get("sample_index_origin", 0)
                ),
                target_sfreq=target_sfreq,
            )
        elif feature.kind == "audio_envelope":
            extracted = audio_envelopes(
                raw,
                snapshot.root,
                (feature,),
                target_sfreq=target_sfreq,
            )
        else:
            raise ValueError(f"Unsupported feature kind {feature.kind!r}")
        names.extend(extracted.names)
        arrays.extend(extracted.arrays)
        counts.update(extracted.event_counts)
        maximum_error = max(maximum_error, extracted.max_quantization_error_seconds)
    return ExtractedFeatures(
        names=tuple(names),
        arrays=tuple(arrays),
        event_counts=counts,
        max_quantization_error_seconds=maximum_error,
        sfreq=target_sfreq,
    )


def prepare_recording(
    raw: mne.io.BaseRaw,
    external_raw: mne.io.BaseRaw | None,
    extracted: ExtractedFeatures,
    recipe: ConversionRecipe,
) -> CNDRecording:
    """Enforce recipe timing limits and construct the neural/stimulus pair."""
    expected_sfreq = recipe.synchronization.get("target_sampling_rate_hz")
    if expected_sfreq is not None and not np.isclose(
        float(expected_sfreq), float(raw.info["sfreq"]), rtol=0, atol=1e-12
    ):
        raise ValueError(
            "Source sampling frequency does not match the reviewed recipe: "
            f"expected {float(expected_sfreq):g} Hz, "
            f"observed {float(raw.info['sfreq']):g} Hz"
        )
    maximum_error_samples = recipe.validation.get(
        "max_event_quantization_error_samples"
    )
    if maximum_error_samples is not None:
        observed_error_samples = extracted.max_quantization_error_seconds * float(
            extracted.sfreq
        )
        if observed_error_samples > float(maximum_error_samples) + 1e-12:
            raise ValueError(
                "Event quantization exceeds the reviewed recipe limit: "
                f"{observed_error_samples:g} samples"
            )
    stimulus = CNDStimulus(
        names=extracted.names,
        features=tuple((array[:, None],) for array in extracted.arrays),
        sfreq=extracted.sfreq,
        stimulus_indices=(1,),
        condition_indices=(1,),
        condition_names=(str(recipe.trials["condition_name"]),),
        cnd_version=1.0,
    )
    recording = from_mne(
        raw,
        stimulus=stimulus,
        external_raws=external_raw,
        external_unit=(
            str(recipe.output.get("external_unit", "V"))
            if external_raw is not None
            else None
        ),
        external_description=(
            str(
                recipe.selection.get(
                    "external_description", "Auxiliary source channels"
                )
            )
            if external_raw is not None
            else None
        ),
        output_unit=str(recipe.output.get("neural_unit", "V")),
        device_name=_device_name(raw, recipe),
        cnd_version=1.0,
        on_unsupported_metadata="ignore",
    )
    return recording


@dataclass(slots=True, frozen=True)
class PreparedConversion:
    recipe: ConversionRecipe
    snapshot: SourceSnapshot
    raw: mne.io.BaseRaw
    external_raw: mne.io.BaseRaw | None
    extracted: ExtractedFeatures
    recording: CNDRecording
    report: ValidationReport


def prepare_conversion(
    recipe: ConversionRecipe, cache_root: str | Path, source_override: str | Path | None
) -> PreparedConversion:
    """Acquire the source and construct a validated recording without writing it."""
    snapshot = acquire_source(
        recipe.source, cache_root, source_override=source_override
    )
    source_raw = read_raw(snapshot.path, recipe.selection, source_root=snapshot.root)
    raw, external_raw = split_eeg_and_external(source_raw)
    extracted = _extract_features(raw, recipe, snapshot)
    recording = prepare_recording(raw, external_raw, extracted, recipe)
    if recording.neural is None:
        raise RuntimeError("MNE conversion did not produce CND neural data")
    strict_report = validate_cnd(recording, strict_spec=True)
    _raise_validation_errors(strict_report)
    return PreparedConversion(
        recipe, snapshot, raw, external_raw, extracted, recording, strict_report
    )
