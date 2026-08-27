"""Signal-reader adapters that normalize supported files into MNE Raw."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mne


class UnsupportedSignalFormatError(ValueError):
    """No reviewed signal adapter exists for the requested input."""


def read_raw(path: str | Path, selection: dict[str, Any]) -> mne.io.BaseRaw:
    """Read EDF/BDF, BrainVision, FIF, EEGLAB, or GDF without preprocessing."""
    source = Path(path)
    reader = str(selection.get("reader", "auto")).lower()
    if reader == "auto":
        reader = _reader_from_suffix(source)

    if reader == "edf":
        raw = mne.io.read_raw_edf(source, preload=False, verbose="ERROR")
    elif reader == "bdf":
        raw = mne.io.read_raw_bdf(source, preload=False, verbose="ERROR")
    elif reader == "brainvision":
        raw = mne.io.read_raw_brainvision(source, preload=False, verbose="ERROR")
    elif reader == "fif":
        raw = mne.io.read_raw_fif(source, preload=False, verbose="ERROR")
    elif reader == "eeglab":
        raw = mne.io.read_raw_eeglab(source, preload=False, verbose="ERROR")
    elif reader == "gdf":
        raw = mne.io.read_raw_gdf(source, preload=False, verbose="ERROR")
    else:
        raise UnsupportedSignalFormatError(f"Unsupported signal reader {reader!r}")

    if selection.get("standardize") == "eegbci":
        mne.datasets.eegbci.standardize(raw)
    montage = selection.get("montage")
    if montage:
        raw.set_montage(str(montage), on_missing="raise", verbose="ERROR")

    if not raw.ch_names:
        raise ValueError("Source recording has no signal channels")
    if any(channel_type != "eeg" for channel_type in raw.get_channel_types()):
        raise ValueError("The EEG converter requires every selected channel to be EEG")
    return raw


def _reader_from_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    readers = {
        ".edf": "edf",
        ".bdf": "bdf",
        ".vhdr": "brainvision",
        ".fif": "fif",
        ".set": "eeglab",
        ".gdf": "gdf",
    }
    try:
        return readers[suffix]
    except KeyError as error:
        raise UnsupportedSignalFormatError(
            f"Cannot infer a reader from extension {suffix!r}"
        ) from error
