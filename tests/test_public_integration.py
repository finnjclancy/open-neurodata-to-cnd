from __future__ import annotations

import os
from pathlib import Path

import pytest

from neurodata_cnd.pipeline import convert_recipe


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_PUBLIC_DATA_TESTS") != "1",
    reason="set RUN_PUBLIC_DATA_TESTS=1 to download the pinned public EDF fixture",
)
def test_eegmmidb_public_vertical_slice(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = convert_recipe(
        root / "recipes" / "eegmmidb-s001-r03.json",
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
    )

    assert result.n_channels == 64
    assert result.n_features == 3
    assert result.event_counts == {
        "rest_onset": 15,
        "left_fist_execution_onset": 8,
        "right_fist_execution_onset": 7,
    }


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_LARGE_PUBLIC_DATA_TESTS") != "1",
    reason=(
        "set RUN_LARGE_PUBLIC_DATA_TESTS=1 to download the pinned 105 MB BIDS fixture"
    ),
)
def test_ds004574_public_bids_vertical_slice(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = convert_recipe(
        root / "recipes" / "ds004574-sub001-oddball.json",
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "outputs",
    )

    assert result.n_channels == 63
    assert result.n_samples == 408_100
    assert result.n_features == 3
    assert result.event_counts == {
        "precue_onset": 236,
        "go_arrow_onset": 236,
        "response_onset": 236,
    }
