"""Reproducible CND/TRF compatibility smoke checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np
from cnd_mne import read_cnd, validate_cnd
from scipy.signal import resample_poly


@dataclass(slots=True, frozen=True)
class AnalysisCheck:
    strict_cnd: str
    feature: str
    neural_sfreq: float
    stimulus_sfreq: float
    aligned_samples: int
    lag_samples: tuple[int, ...]
    design_shape: tuple[int, int]
    response_shape: tuple[int, int]
    finite_weights: bool
    nonzero_feature_samples: int
    checked_trial_index: int
    total_trials: int
    predictor_standard_deviation: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def check_cnsp_trf_compatibility(
    neural_path: str | Path,
    stimulus_path: str | Path,
    *,
    feature: str | None = None,
    lag_min_ms: float = 0.0,
    lag_max_ms: float = 400.0,
    ridge: float = 1.0,
    max_samples: int = 20_000,
) -> AnalysisCheck:
    """Load CND and solve a small forward ridge TRF on aligned samples.

    This is a Python smoke check: MAT-file loading, strict
    CND fields, stimulus/neural clock reconciliation, lag construction, and a
    finite multichannel ridge solution. It does not replace executing an
    official MATLAB tutorial in MATLAB.
    """
    if not np.isfinite(ridge) or ridge <= 0:
        raise ValueError("ridge must be finite and positive")
    if max_samples < 3:
        raise ValueError("max_samples must be at least three")
    if not np.isfinite([lag_min_ms, lag_max_ms]).all():
        raise ValueError("lag bounds must be finite")
    recording = read_cnd(neural_path, stimulus_path=stimulus_path)
    report = validate_cnd(recording, strict_spec=True)
    neural = recording.neural
    stimulus = recording.stimulus
    if neural is None or stimulus is None:
        raise ValueError("TRF compatibility requires neural and stimulus data")
    separate_clocks = not np.isclose(stimulus.sfreq, neural.sfreq, rtol=0, atol=0)
    errors = [
        issue
        for issue in report.errors
        if not (separate_clocks and issue.code == "sampling_frequency_mismatch")
    ]
    if errors:
        messages = "; ".join(f"{issue.path}: {issue.message}" for issue in errors)
        raise ValueError(messages)
    if not neural.trials or not stimulus.features:
        raise ValueError("TRF compatibility requires at least one trial and feature")
    feature_name = feature or stimulus.names[0]
    stimulus_trial = np.asarray(stimulus.feature(feature_name)[0], dtype=np.float64)
    if stimulus_trial.ndim != 1:
        raise ValueError("TRF smoke check requires a one-dimensional feature")
    if not np.isclose(stimulus.sfreq, neural.sfreq, rtol=0, atol=0):
        ratio = Fraction(neural.sfreq / stimulus.sfreq).limit_denominator(100_000)
        stimulus_trial = resample_poly(
            stimulus_trial, ratio.numerator, ratio.denominator
        )
    response = np.asarray(neural.trials[0], dtype=np.float64)
    n_samples = min(len(stimulus_trial), response.shape[0], max_samples)
    if n_samples < 3:
        raise ValueError("TRF smoke check needs at least three aligned samples")
    stimulus_trial = stimulus_trial[:n_samples]
    response = response[:n_samples]
    if not np.isfinite(stimulus_trial).all() or not np.isfinite(response).all():
        raise ValueError("TRF smoke check requires finite data")
    predictor_std = float(np.std(stimulus_trial))
    if predictor_std == 0:
        raise ValueError(
            "TRF smoke check requires predictor variation in the checked window"
        )
    lag_start = int(round(lag_min_ms * neural.sfreq / 1000.0))
    lag_stop = int(round(lag_max_ms * neural.sfreq / 1000.0))
    if lag_stop < lag_start:
        raise ValueError("lag_max_ms must be at least lag_min_ms")
    lags = np.arange(lag_start, lag_stop + 1, dtype=int)
    design = _lag_matrix(stimulus_trial, lags)
    design -= design.mean(axis=0, keepdims=True)
    response = response - response.mean(axis=0, keepdims=True)
    gram = design.T @ design
    weights = np.linalg.solve(
        gram + float(ridge) * np.eye(gram.shape[0]), design.T @ response
    )
    if not np.isfinite(weights).all():
        raise ValueError("TRF smoke check produced non-finite weights")
    return AnalysisCheck(
        strict_cnd="pass",
        feature=feature_name,
        neural_sfreq=float(neural.sfreq),
        stimulus_sfreq=float(stimulus.sfreq),
        aligned_samples=n_samples,
        lag_samples=tuple(int(value) for value in lags),
        design_shape=design.shape,
        response_shape=response.shape,
        finite_weights=bool(np.isfinite(weights).all()),
        nonzero_feature_samples=int(np.count_nonzero(stimulus_trial)),
        checked_trial_index=0,
        total_trials=len(neural.trials),
        predictor_standard_deviation=predictor_std,
    )


def _lag_matrix(feature: np.ndarray, lags: np.ndarray) -> np.ndarray:
    if np.any(np.abs(lags) >= feature.size):
        raise ValueError("Requested lags must be shorter than the checked recording")
    output = np.zeros((feature.size, lags.size), dtype=np.float64)
    for column, lag in enumerate(lags):
        if lag >= 0:
            output[lag:, column] = feature[: feature.size - lag] if lag else feature
        else:
            output[:lag, column] = feature[-lag:]
    return output
