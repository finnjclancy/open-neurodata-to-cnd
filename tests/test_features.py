from __future__ import annotations

import pytest
from conftest import synthetic_raw

from neurodata_cnd.features import MissingAnnotationError, annotation_impulses
from neurodata_cnd.recipe import FeatureSpec


def test_annotation_impulses_preserve_event_samples() -> None:
    raw = synthetic_raw()
    features = annotation_impulses(
        raw,
        (
            FeatureSpec("a_onset", "annotation_impulse", "A", "binary"),
            FeatureSpec("b_onset", "annotation_impulse", "B", "binary"),
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
            (FeatureSpec("missing", "annotation_impulse", "missing", "binary"),),
        )
