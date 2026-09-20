"""Turn event annotations into stimulus impulse tracks."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import mne
import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile
from scipy.signal import hilbert, resample_poly

from .recipe import FeatureSpec


class MissingAnnotationError(ValueError):
    """A reviewed annotation mapping is absent from a source recording."""


@dataclass(slots=True, frozen=True)
class ExtractedFeatures:
    names: tuple[str, ...]
    arrays: tuple[NDArray[np.float64], ...]
    event_counts: dict[str, int]
    max_quantization_error_seconds: float
    sfreq: float


def annotation_impulses(
    raw: mne.io.BaseRaw,
    specifications: tuple[FeatureSpec, ...],
    *,
    target_sfreq: float | None = None,
) -> ExtractedFeatures:
    """Map explicitly named annotations to one-sample CND impulse vectors."""
    events, event_ids = mne.events_from_annotations(
        raw, event_id=None, use_rounding=True, regexp=None, verbose="ERROR"
    )
    resolved_sfreq = float(target_sfreq or raw.info["sfreq"])
    n_times = _target_sample_count(raw, resolved_sfreq)
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
        source_samples = (
            events[events[:, 2] == code, 0].astype(np.int64) - raw.first_samp
        )
        source_times = source_samples / float(raw.info["sfreq"])
        samples = np.rint(source_times * resolved_sfreq).astype(np.int64)
        if np.any(samples < 0) or np.any(samples >= n_times):
            raise ValueError(
                f"Annotation {specification.source_annotation!r} maps outside "
                "the signal"
            )
        if np.unique(samples).size != samples.size:
            raise ValueError(
                "Multiple selected annotations occupy the same target sample"
            )
        impulse = np.zeros(n_times, dtype=np.float64)
        impulse[samples] = 1.0
        arrays.append(impulse)
        counts[specification.name] = int(samples.size)
        event_samples_by_label[specification.source_annotation] = samples

    max_error = _maximum_quantization_error(
        raw, event_samples_by_label, represented_sfreq=resolved_sfreq
    )
    return ExtractedFeatures(
        names=tuple(specification.name for specification in specifications),
        arrays=tuple(arrays),
        event_counts=counts,
        max_quantization_error_seconds=max_error,
        sfreq=resolved_sfreq,
    )


def bids_event_impulses(
    raw: mne.io.BaseRaw,
    events_path: str | Path,
    specifications: tuple[FeatureSpec, ...],
    *,
    sample_index_origin: int = 0,
    target_sfreq: float | None = None,
) -> ExtractedFeatures:
    """Map reviewed BIDS event-table values to source-clock impulse vectors."""
    if sample_index_origin not in {0, 1}:
        raise ValueError("BIDS sample_index_origin must be 0 or 1")
    with Path(events_path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or "onset" not in rows[0]:
        raise ValueError(f"BIDS event table is empty or lacks onset: {events_path}")

    arrays: list[NDArray[np.float64]] = []
    counts: dict[str, int] = {}
    quantization_errors: list[float] = []
    source_sfreq = float(raw.info["sfreq"])
    resolved_sfreq = float(target_sfreq or source_sfreq)
    n_times = _target_sample_count(raw, resolved_sfreq)
    for specification in specifications:
        column = specification.source_column
        values = (
            (specification.source_value,)
            if specification.source_value is not None
            else specification.source_values
        )
        if column is None or values is None:
            raise ValueError(
                "BIDS event feature lacks source_column and event value selector"
            )
        if column not in rows[0]:
            raise ValueError(f"BIDS event table lacks reviewed column {column!r}")
        matching = [row for row in rows if row.get(column) in values]
        if not matching:
            selector = values[0] if len(values) == 1 else list(values)
            raise MissingAnnotationError(
                f"No BIDS events match {column}={selector!r} for {specification.name!r}"
            )
        impulse = np.zeros(n_times, dtype=np.float64)
        for row in matching:
            onset = float(row["onset"])
            onset_sample = int(round(onset * source_sfreq))
            source_sample = _optional_sample(row.get("sample"))
            source_zero_based = (
                onset_sample
                if source_sample is None
                else source_sample - sample_index_origin
            )
            source_time = source_zero_based / source_sfreq
            sample = int(round(source_time * resolved_sfreq))
            if sample < 0 or sample >= n_times:
                raise ValueError(
                    f"BIDS event {column}={row.get(column)!r} maps outside the signal"
                )
            if impulse[sample] != 0:
                raise ValueError(
                    f"Multiple selected {column} events occupy sample {sample}"
                )
            quantization_errors.append(abs(sample / resolved_sfreq - onset))
            impulse[sample] = 1.0
        arrays.append(impulse)
        counts[specification.name] = len(matching)
    return ExtractedFeatures(
        names=tuple(specification.name for specification in specifications),
        arrays=tuple(arrays),
        event_counts=counts,
        max_quantization_error_seconds=max(quantization_errors, default=0.0),
        sfreq=resolved_sfreq,
    )


def audio_envelopes(
    raw: mne.io.BaseRaw,
    source_root: str | Path,
    specifications: tuple[FeatureSpec, ...],
    *,
    target_sfreq: float,
) -> ExtractedFeatures:
    """Create configurable, first-sample-aligned envelopes from WAV stimuli."""
    n_times = _target_sample_count(raw, target_sfreq)
    arrays: list[NDArray[np.float64]] = []
    for specification in specifications:
        if specification.source is None or specification.method is None:
            raise ValueError("Audio envelope requires source and method")
        path = Path(source_root) / specification.source
        if not path.is_file():
            raise FileNotFoundError(path)
        source_sfreq, audio = wavfile.read(path)
        signal = _audio_as_float(audio)
        if signal.ndim == 2:
            signal = signal.mean(axis=1)
        start = int(round(specification.offset_seconds * float(source_sfreq)))
        if start >= signal.size:
            raise ValueError(f"Audio offset lies beyond stimulus file: {path}")
        signal = signal[start:]
        if specification.method == "hilbert":
            envelope = np.abs(hilbert(signal))
        elif specification.method == "rectified":
            envelope = np.abs(signal)
        else:
            raise ValueError(f"Unsupported envelope method {specification.method!r}")
        envelope = np.power(envelope, specification.compression)
        ratio = Fraction(float(target_sfreq) / float(source_sfreq)).limit_denominator(
            100_000
        )
        envelope = resample_poly(envelope, ratio.numerator, ratio.denominator)
        envelope = _normalize_envelope(envelope, specification.normalization)
        if abs(envelope.size - n_times) > 1:
            raise ValueError(
                f"Audio envelope {specification.name!r} has {envelope.size} samples; "
                f"expected {n_times} for first-sample-aligned EEG duration"
            )
        if envelope.size < n_times:
            envelope = np.pad(envelope, (0, n_times - envelope.size))
        arrays.append(np.asarray(envelope[:n_times], dtype=np.float64))
    return ExtractedFeatures(
        names=tuple(specification.name for specification in specifications),
        arrays=tuple(arrays),
        event_counts={},
        max_quantization_error_seconds=0.0,
        sfreq=float(target_sfreq),
    )


def _optional_sample(value: str | None) -> int | None:
    if value is None or value.strip().lower() in {"", "n/a"}:
        return None
    numeric = float(value)
    if not numeric.is_integer():
        raise ValueError(f"BIDS sample value must be an integer, found {value!r}")
    return int(numeric)


def _maximum_quantization_error(
    raw: mne.io.BaseRaw,
    samples_by_label: dict[str, NDArray[np.int64]],
    *,
    represented_sfreq: float,
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
        represented_time = sample / represented_sfreq
        source_time = float(onset) - raw.first_time
        errors.append(abs(represented_time - source_time))
    return max(errors, default=0.0)


def _target_sample_count(raw: mne.io.BaseRaw, target_sfreq: float) -> int:
    if not np.isfinite(target_sfreq) or target_sfreq <= 0:
        raise ValueError("target stimulus sampling rate must be positive")
    return int(round(raw.n_times * target_sfreq / float(raw.info["sfreq"])))


def _audio_as_float(audio: NDArray[np.generic]) -> NDArray[np.float64]:
    array = np.asarray(audio)
    if np.issubdtype(array.dtype, np.integer):
        info = np.iinfo(array.dtype)
        scale = float(max(abs(info.min), info.max))
        if np.issubdtype(array.dtype, np.unsignedinteger):
            midpoint = (float(info.max) + 1.0) / 2.0
            return (array.astype(np.float64) - midpoint) / midpoint
        return array.astype(np.float64) / scale
    return array.astype(np.float64)


def _normalize_envelope(
    envelope: NDArray[np.float64], normalization: str
) -> NDArray[np.float64]:
    if normalization == "none":
        return envelope
    if normalization == "peak":
        peak = float(np.max(np.abs(envelope)))
        return envelope / peak if peak else envelope
    if normalization == "zscore":
        scale = float(np.std(envelope))
        return (envelope - float(np.mean(envelope))) / scale if scale else envelope * 0
    raise ValueError(f"Unsupported envelope normalization {normalization!r}")
