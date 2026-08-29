from __future__ import annotations

import numpy as np
import pytest
from conftest import synthetic_raw

from neurodata_cnd.features import MissingAnnotationError, annotation_impulses
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
