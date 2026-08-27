"""Stimulus feature extraction from source recording annotations."""

from __future__ import annotations

from dataclasses import dataclass

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
