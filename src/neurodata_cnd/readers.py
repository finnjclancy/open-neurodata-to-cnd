"""Load EDF, BIDS, and similar files as MNE ``Raw``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mne


class UnsupportedSignalFormatError(ValueError):
    """No reviewed signal adapter exists for the requested input."""


def read_raw(
    path: str | Path,
    selection: dict[str, Any],
    *,
    source_root: str | Path | None = None,
) -> mne.io.BaseRaw:
    """Read EDF/BDF, BrainVision, FIF, EEGLAB, or GDF without preprocessing."""
    source = Path(path)
    reader = str(selection.get("reader", "auto")).lower()
    if reader == "auto":
        reader = _reader_from_suffix(source)

    if reader == "bids":
        if source_root is None:
            raise ValueError("The BIDS reader requires a source snapshot root")
        from mne_bids import BIDSPath, read_raw_bids

        extension = selection.get("extension")
        bids_path = BIDSPath(
            root=Path(source_root),
            subject=str(selection["subject"]),
            session=_optional_entity(selection, "session"),
            task=str(selection["task"]),
            acquisition=_optional_entity(selection, "acquisition"),
            run=_optional_entity(selection, "run"),
            datatype="eeg",
            suffix="eeg",
            extension=str(extension) if extension else None,
        )
        if bids_path.fpath.resolve() != source.resolve():
            raise ValueError(
                "The BIDS entities resolve to a recording other than "
                "source.primary_path"
            )
        raw = read_raw_bids(
            bids_path,
            extra_params={"preload": False},
            verbose="ERROR",
        )
    elif reader == "edf":
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
    channel_type_policy = selection.get("channel_type_policy")
    if channel_type_policy == "all_eeg":
        evidence = str(selection.get("channel_type_evidence", "")).strip()
        if not evidence:
            raise ValueError("all_eeg channel typing requires recorded evidence")
        raw.set_channel_types({name: "eeg" for name in raw.ch_names}, verbose="ERROR")
    elif channel_type_policy == "eeg_only":
        eeg_channels = [
            name
            for name, channel_type in zip(
                raw.ch_names, raw.get_channel_types(), strict=True
            )
            if channel_type == "eeg"
        ]
        if not eeg_channels:
            raise ValueError("The source recording contains no EEG channels")
        raw.pick(eeg_channels)
    elif channel_type_policy not in {None, "source"}:
        raise ValueError(f"Unsupported channel type policy {channel_type_policy!r}")
    if any(channel_type != "eeg" for channel_type in raw.get_channel_types()):
        raise ValueError("The EEG converter requires every selected channel to be EEG")
    return raw


def _optional_entity(selection: dict[str, Any], key: str) -> str | None:
    value = selection.get(key)
    return str(value) if value is not None else None


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
