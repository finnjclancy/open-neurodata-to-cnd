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


def test_explicit_eeg_channel_correction_requires_evidence(tmp_path: Path) -> None:
    raw = synthetic_raw()
    raw.set_channel_types({name: "misc" for name in raw.ch_names})
    source = tmp_path / "misc_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")

    with pytest.raises(ValueError, match="requires recorded evidence"):
        read_raw(source, {"reader": "fif", "channel_type_policy": "all_eeg"})

    loaded = read_raw(
        source,
        {
            "reader": "fif",
            "channel_type_policy": "all_eeg",
            "channel_type_evidence": "Reviewed source sidecar declares EEG channels.",
        },
    )
    assert loaded.get_channel_types() == ["eeg", "eeg"]


def test_eeg_only_channel_policy_excludes_auxiliary_channels(tmp_path: Path) -> None:
    raw = synthetic_raw()
    auxiliary = mne.io.RawArray(
        [[0.0] * raw.n_times],
        mne.create_info(["VEOG"], raw.info["sfreq"], ["eog"]),
        verbose="ERROR",
    )
    raw.add_channels([auxiliary])
    source = tmp_path / "mixed_raw.fif"
    raw.save(source, overwrite=True, verbose="ERROR")

    loaded = read_raw(source, {"reader": "fif", "channel_type_policy": "eeg_only"})

    assert loaded.ch_names == ["Fz", "Cz"]
    assert loaded.get_channel_types() == ["eeg", "eeg"]
