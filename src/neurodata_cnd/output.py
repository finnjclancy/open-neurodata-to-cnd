"""Serialize a prepared conversion, verify it, and record provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from cnd_mne import read_cnd, validate_cnd, write_cnd

from .manifest import build_manifest, content_sha256
from .preparation import PreparedConversion
from .round_trip import _check_round_trip, _raise_validation_errors


def write_verified_conversion(
    prepared: PreparedConversion, staging: Path
) -> tuple[Path, Path]:
    """Write only into an unpublished staging directory."""
    recipe, snapshot = prepared.recipe, prepared.snapshot
    raw, external_raw = prepared.raw, prepared.external_raw
    extracted, recording = prepared.extracted, prepared.recording
    if recording.neural is None:
        raise RuntimeError("MNE conversion did not produce CND neural data")
    mat_version = cast(Literal["5", "7.3"], str(recipe.output.get("mat_version", "5")))
    paths = write_cnd(
        recording,
        staging / "dataCND",
        subject=str(recipe.selection["subject"]),
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
    _raise_validation_errors(round_trip_report)
    channel_location_check = _check_round_trip(
        raw,
        external_raw,
        round_trip,
        extracted,
        recipe,
        str(recording.neural.data_unit),
    )

    manifest = build_manifest(
        recipe,
        snapshot,
        raw,
        extracted.event_counts,
        extracted.max_quantization_error_seconds,
        paths.neural,
        paths.stimulus,
        prepared.report,
        round_trip_report,
        content_sha256(round_trip),
        external_raw,
        channel_location_check,
    )
    (staging / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return paths.neural, paths.stimulus
