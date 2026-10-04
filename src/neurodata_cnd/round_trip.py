"""Check conversion values, coordinates, and the CND contract."""

from __future__ import annotations

import mne
import numpy as np
from cnd_mne import CNDRecording, ValidationReport, to_mne

from .features import ExtractedFeatures
from .recipe import ConversionRecipe


def _check_round_trip(
    raw: mne.io.BaseRaw,
    external_raw: mne.io.BaseRaw | None,
    recording: CNDRecording,
    extracted: ExtractedFeatures,
    recipe: ConversionRecipe,
    neural_unit: str,
) -> str:
    """Compare EEG, auxiliary signals, coordinates, and features after MATLAB I/O."""
    if recording.stimulus is None:
        raise RuntimeError("CND read-back did not contain stimulus data")
    mne_recording = to_mne(recording, neural_unit=neural_unit)
    if len(mne_recording.raws) != 1:
        raise RuntimeError("Expected exactly one round-trip CND trial")
    if not np.allclose(
        mne_recording.raws[0].get_data(), raw.get_data(), rtol=1e-7, atol=1e-12
    ):
        raise RuntimeError("CND-to-MNE numerical round trip changed the EEG values")
    if external_raw is not None:
        recording_external = mne_recording.external_raws(
            unit=str(recipe.output.get("external_unit", "V")),
            channel_names=external_raw.ch_names,
            channel_types=external_raw.get_channel_types(),
        )[0]
        if not np.allclose(
            recording_external.get_data(),
            external_raw.get_data(),
            rtol=1e-7,
            atol=1e-12,
        ):
            raise RuntimeError(
                "CND-to-MNE numerical round trip changed external-channel values"
            )
    channel_location_check = _check_channel_location_round_trip(
        raw, recording, neural_unit
    )
    for name, expected in zip(extracted.names, extracted.arrays, strict=True):
        observed = np.asarray(recording.stimulus.feature(name)[0]).squeeze()
        if not np.array_equal(observed, expected):
            raise RuntimeError(f"CND round trip changed stimulus feature {name!r}")

    return channel_location_check


def _raise_validation_errors(report: ValidationReport) -> None:
    if report.errors:
        raise ValueError(
            "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
        )


def _check_channel_location_round_trip(
    source: mne.io.BaseRaw, recording: CNDRecording, neural_unit: str
) -> str:
    source_montage = source.get_montage()
    if source_montage is None:
        return "not_available"
    restored = to_mne(
        recording,
        neural_unit=neural_unit,
        montage="eeglab",
        coordinate_scale_to_meters=1.0,
    ).raws[0]
    restored_montage = restored.get_montage()
    if restored_montage is None:
        raise RuntimeError("CND-to-MNE round trip lost channel locations")
    source_positions = source_montage.get_positions()["ch_pos"]
    restored_positions = restored_montage.get_positions()["ch_pos"]
    for name in source.ch_names:
        if name not in source_positions or name not in restored_positions:
            raise RuntimeError(f"CND-to-MNE round trip lost channel location {name!r}")
        if not np.allclose(
            source_positions[name], restored_positions[name], rtol=0, atol=1e-12
        ):
            raise RuntimeError(
                f"CND-to-MNE round trip changed channel location {name!r}"
            )
    return "pass"
