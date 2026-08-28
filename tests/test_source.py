from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from neurodata_cnd.recipe import SourceFileSpec, SourceSpec
from neurodata_cnd.source import SourceIntegrityError, acquire_source


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_multifile_snapshot_is_pinned_and_reused(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    first = upstream / "recording.set"
    second = upstream / "recording.fdt"
    first.write_bytes(b"header")
    second.write_bytes(b"samples")
    source = SourceSpec(
        dataset_id="example",
        provider="fixture",
        url="https://example.test/dataset",
        version="1.0.0",
        primary_path="sub-01/eeg/recording.set",
        files=(
            SourceFileSpec(
                path="sub-01/eeg/recording.set",
                url=first.as_uri(),
                sha256=_digest(b"header"),
            ),
            SourceFileSpec(
                path="sub-01/eeg/recording.fdt",
                url=second.as_uri(),
                sha256=_digest(b"samples"),
            ),
        ),
    )

    downloaded = acquire_source(source, tmp_path / "cache")
    reused = acquire_source(source, tmp_path / "cache")

    assert downloaded.path == downloaded.root / source.primary_path
    assert downloaded.reused_cache is False
    assert reused.reused_cache is True
    assert reused.sha256 == downloaded.sha256
    assert [record["path"] for record in reused.files] == [
        "sub-01/eeg/recording.set",
        "sub-01/eeg/recording.fdt",
    ]


def test_cached_snapshot_file_is_reverified(tmp_path: Path) -> None:
    upstream = tmp_path / "source.edf"
    upstream.write_bytes(b"reviewed")
    source = SourceSpec(
        dataset_id="example",
        provider="fixture",
        url="https://example.test/dataset",
        version="1.0.0",
        primary_path="source.edf",
        files=(
            SourceFileSpec(
                path="source.edf",
                url=upstream.as_uri(),
                sha256=_digest(b"reviewed"),
            ),
        ),
    )
    snapshot = acquire_source(source, tmp_path / "cache")
    snapshot.path.write_bytes(b"corrupt")

    with pytest.raises(SourceIntegrityError, match="SHA-256 mismatch"):
        acquire_source(source, tmp_path / "cache")
