from __future__ import annotations

import numpy as np
import pytest
from conftest import synthetic_raw
from scipy.io import wavfile

from neurodata_cnd.features import (
    MissingAnnotationError,
    annotation_impulses,
    audio_envelopes,
)
from neurodata_cnd.recipe import FeatureSpec


def test_annotation_impulses_preserve_event_samples() -> None:
    raw = synthetic_raw()
    features = annotation_impulses(
        raw,
        (
            FeatureSpec(
                "a_onset", "annotation_impulse", "binary", source_annotation="A"
            ),
            FeatureSpec(
                "b_onset", "annotation_impulse", "binary", source_annotation="B"
            ),
        ),
    )

    assert features.names == ("a_onset", "b_onset")
    assert features.event_counts == {"a_onset": 2, "b_onset": 1}
    assert features.arrays[0].nonzero()[0].tolist() == [50, 350]
    assert features.arrays[1].nonzero()[0].tolist() == [200]
    assert features.max_quantization_error_seconds == pytest.approx(0.0)


def test_annotation_impulses_fail_when_reviewed_event_is_missing() -> None:
    with pytest.raises(MissingAnnotationError, match="Required annotation 'missing'"):
        annotation_impulses(
            synthetic_raw(),
            (
                FeatureSpec(
                    "missing",
                    "annotation_impulse",
                    "binary",
                    source_annotation="missing",
                ),
            ),
        )


def test_bids_event_impulses_prefer_sample_and_reconcile_onset(tmp_path) -> None:
    from neurodata_cnd.features import bids_event_impulses

    events = tmp_path / "events.tsv"
    events.write_text(
        "onset\tduration\tsample\tvalue\n"
        "0.5\t0\t50\tstandard\n"
        "2.0\t0\t200\ttarget\n"
        "3.5\t0\t350\tstandard\n",
        encoding="utf-8",
    )
    features = bids_event_impulses(
        synthetic_raw(),
        events,
        (
            FeatureSpec(
                "standard_onset",
                "bids_event_impulse",
                "binary",
                source_column="value",
                source_value="standard",
            ),
            FeatureSpec(
                "target_onset",
                "bids_event_impulse",
                "binary",
                source_column="value",
                source_value="target",
            ),
        ),
    )

    assert np.flatnonzero(features.arrays[0]).tolist() == [50, 350]
    assert np.flatnonzero(features.arrays[1]).tolist() == [200]
    assert features.event_counts == {"standard_onset": 2, "target_onset": 1}
    assert features.max_quantization_error_seconds == pytest.approx(0.0)


def test_bids_event_impulses_can_combine_reviewed_values(tmp_path) -> None:
    from neurodata_cnd.features import bids_event_impulses

    events = tmp_path / "events.tsv"
    events.write_text(
        "onset\tduration\tsample\tvalue\n"
        "0.5\t0\t50\t11\n"
        "2.0\t0\t200\t22\n"
        "3.5\t0\t350\t31\n",
        encoding="utf-8",
    )
    features = bids_event_impulses(
        synthetic_raw(),
        events,
        (
            FeatureSpec(
                "target_onset",
                "bids_event_impulse",
                "binary",
                source_column="value",
                source_values=("11", "22"),
            ),
        ),
    )

    assert np.flatnonzero(features.arrays[0]).tolist() == [50, 200]
    assert features.event_counts == {"target_onset": 2}


def test_bids_event_impulses_support_explicit_one_based_samples(tmp_path) -> None:
    from neurodata_cnd.features import bids_event_impulses

    events = tmp_path / "events.tsv"
    events.write_text(
        "onset\tduration\tsample\tvalue\n0.5\t0\t51\ttarget\n",
        encoding="utf-8",
    )
    features = bids_event_impulses(
        synthetic_raw(),
        events,
        (
            FeatureSpec(
                "target_onset",
                "bids_event_impulse",
                "binary",
                source_column="value",
                source_value="target",
            ),
        ),
        sample_index_origin=1,
    )

    assert np.flatnonzero(features.arrays[0]).tolist() == [50]
    assert features.max_quantization_error_seconds == pytest.approx(0.0)


def test_event_features_can_keep_a_separate_stimulus_clock() -> None:
    features = annotation_impulses(
        synthetic_raw(),
        (
            FeatureSpec(
                "a_onset", "annotation_impulse", "binary", source_annotation="A"
            ),
        ),
        target_sfreq=50.0,
    )

    assert features.sfreq == 50.0
    assert features.arrays[0].shape == (250,)
    assert np.flatnonzero(features.arrays[0]).tolist() == [25, 175]


@pytest.mark.parametrize("method", ["hilbert", "rectified"])
def test_audio_envelope_method_is_configurable(tmp_path, method: str) -> None:
    source_sfreq = 1_000
    times = np.arange(5 * source_sfreq) / source_sfreq
    carrier = 0.5 * np.sin(2 * np.pi * 40 * times)
    modulation = 1.0 + 0.5 * np.sin(2 * np.pi * 2 * times)
    wavfile.write(tmp_path / "speech.wav", source_sfreq, carrier * modulation)

    features = audio_envelopes(
        synthetic_raw(),
        tmp_path,
        (
            FeatureSpec(
                "speech_envelope",
                "audio_envelope",
                "normalized_amplitude",
                source="speech.wav",
                method=method,
                compression=0.6,
                normalization="peak",
            ),
        ),
        target_sfreq=50.0,
    )

    assert features.sfreq == 50.0
    assert features.arrays[0].shape == (250,)
    assert np.isfinite(features.arrays[0]).all()
    assert np.max(np.abs(features.arrays[0])) == pytest.approx(1.0, abs=0.02)


def test_annotation_collision_after_downsampling_is_rejected():
    import mne

    raw = synthetic_raw()
    raw.set_annotations(mne.Annotations([0.10, 0.11], [0, 0], ["A", "A"]))
    with pytest.raises(ValueError, match="same target sample"):
        annotation_impulses(
            raw,
            (FeatureSpec("a", "annotation_impulse", "binary", source_annotation="A"),),
            target_sfreq=10,
        )


def test_unsigned_pcm_is_centered():
    from neurodata_cnd.features import _audio_as_float

    np.testing.assert_array_equal(
        _audio_as_float(np.array([0, 128, 255], dtype=np.uint8)), [-1, 0, 127 / 128]
    )
