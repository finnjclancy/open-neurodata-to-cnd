"""Stimulus feature extraction from source recording annotations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import mne
import numpy as np
from numpy.typing import NDArray

from .recipe import FeatureSpec


class MissingAnnotationError(ValueError):
    """A reviewed annotation mapping is absent from a source recording."""


@dataclass(slots=True, frozen=True)
class ExtractedFeatures:
    names: tuple[str, ...]
    arrays: tuple[NDArray[np.float64], ...]
    event_counts: dict[str, int]
    max_quantization_error_seconds: float


def annotation_impulses(
    raw: mne.io.BaseRaw, specifications: tuple[FeatureSpec, ...]
) -> ExtractedFeatures:
    """Map explicitly named annotations to one-sample CND impulse vectors."""
    events, event_ids = mne.events_from_annotations(
        raw, event_id=None, use_rounding=True, regexp=None, verbose="ERROR"
    )
    arrays: list[NDArray[np.float64]] = []
    counts: dict[str, int] = {}
    event_samples_by_label: dict[str, NDArray[np.int64]] = {}
    for specification in specifications:
        if specification.source_annotation is None:
            raise ValueError("Annotation feature is missing source_annotation")
        try:
            code = event_ids[specification.source_annotation]
        except KeyError as error:
            available = ", ".join(sorted(event_ids)) or "none"
            raise MissingAnnotationError(
                f"Required annotation {specification.source_annotation!r} is absent; "
                f"available annotations: {available}"
            ) from error
        samples = events[events[:, 2] == code, 0].astype(np.int64) - raw.first_samp
        if np.any(samples < 0) or np.any(samples >= raw.n_times):
            raise ValueError(
                f"Annotation {specification.source_annotation!r} maps outside "
                "the signal"
            )
        impulse = np.zeros(raw.n_times, dtype=np.float64)
        impulse[samples] = 1.0
        arrays.append(impulse)
        counts[specification.name] = int(samples.size)
        event_samples_by_label[specification.source_annotation] = samples

    max_error = _maximum_quantization_error(raw, event_samples_by_label)
    return ExtractedFeatures(
        names=tuple(specification.name for specification in specifications),
        arrays=tuple(arrays),
        event_counts=counts,
        max_quantization_error_seconds=max_error,
    )


def bids_event_impulses(
    raw: mne.io.BaseRaw,
    events_path: str | Path,
    specifications: tuple[FeatureSpec, ...],
) -> ExtractedFeatures:
    """Map reviewed BIDS event-table values to source-clock impulse vectors."""
    with Path(events_path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or "onset" not in rows[0]:
        raise ValueError(f"BIDS event table is empty or lacks onset: {events_path}")

    arrays: list[NDArray[np.float64]] = []
    counts: dict[str, int] = {}
    quantization_errors: list[float] = []
    sfreq = float(raw.info["sfreq"])
    for specification in specifications:
        column = specification.source_column
        value = specification.source_value
        if column is None or value is None:
            raise ValueError("BIDS event feature lacks source_column/source_value")
        if column not in rows[0]:
            raise ValueError(f"BIDS event table lacks reviewed column {column!r}")
        matching = [row for row in rows if row.get(column) == value]
        if not matching:
            raise MissingAnnotationError(
                f"No BIDS events match {column}={value!r} for {specification.name!r}"
            )
        impulse = np.zeros(raw.n_times, dtype=np.float64)
        for row in matching:
            onset = float(row["onset"])
            onset_sample = int(round(onset * sfreq))
            source_sample = _optional_sample(row.get("sample"))
            sample = onset_sample if source_sample is None else source_sample
            if sample < 0 or sample >= raw.n_times:
                raise ValueError(
                    f"BIDS event {column}={value!r} maps outside the signal"
                )
            if impulse[sample] != 0:
                raise ValueError(
                    f"Multiple {column}={value!r} events occupy sample {sample}"
                )
            quantization_errors.append(abs(sample / sfreq - onset))
            impulse[sample] = 1.0
        arrays.append(impulse)
        counts[specification.name] = len(matching)
    return ExtractedFeatures(
        names=tuple(specification.name for specification in specifications),
        arrays=tuple(arrays),
        event_counts=counts,
        max_quantization_error_seconds=max(quantization_errors, default=0.0),
    )


def _optional_sample(value: str | None) -> int | None:
    if value is None or value.strip().lower() in {"", "n/a"}:
        return None
    numeric = float(value)
    if not numeric.is_integer():
        raise ValueError(f"BIDS sample value must be an integer, found {value!r}")
    return int(numeric)


def _maximum_quantization_error(
    raw: mne.io.BaseRaw, samples_by_label: dict[str, NDArray[np.int64]]
) -> float:
    pending = {label: list(samples) for label, samples in samples_by_label.items()}
    errors: list[float] = []
    for onset, description in zip(
        raw.annotations.onset, raw.annotations.description, strict=True
    ):
        samples = pending.get(str(description))
        if not samples:
            continue
        sample = samples.pop(0)
        represented_time = sample / float(raw.info["sfreq"])
        source_time = float(onset) - raw.first_time
        errors.append(abs(represented_time - source_time))
    return max(errors, default=0.0)
