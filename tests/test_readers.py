from __future__ import annotations

from pathlib import Path

import mne
import pytest
from conftest import synthetic_raw

from neurodata_cnd.readers import read_raw


@pytest.mark.parametrize(
    ("reader", "suffix", "export_format"),
    [
        ("edf", ".edf", "edf"),
        ("brainvision", ".vhdr", "brainvision"),
    ],
)
def test_exported_signal_formats_load(
    tmp_path: Path, reader: str, suffix: str, export_format: str
) -> None:
    raw = synthetic_raw()
    source = tmp_path / f"recording{suffix}"
    mne.export.export_raw(
        source, raw, fmt=export_format, overwrite=True, verbose="ERROR"
    )

    loaded = read_raw(source, {"reader": reader})

    assert loaded.n_times == raw.n_times
    assert loaded.info["sfreq"] == raw.info["sfreq"]
    assert loaded.get_channel_types() == ["eeg", "eeg"]


def test_fif_signal_format_loads(tmp_path: Path) -> None:
    raw = synthetic_raw()
    source = tmp_path / "recording_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")

    loaded = read_raw(source, {"reader": "auto"})

    assert loaded.n_times == raw.n_times
    assert loaded.ch_names == raw.ch_names
    assert tuple(loaded.annotations.description) == ("A", "B", "A")
