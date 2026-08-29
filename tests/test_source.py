from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from neurodata_cnd.recipe import SourceFileSpec, SourceSpec
from neurodata_cnd.source import SourceIntegrityError, acquire_source


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_digest(value: bytes) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(value)}\0".encode())
    digest.update(value)
    return digest.hexdigest()


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


def test_git_blob_checksum_is_supported_for_small_bids_metadata(
    tmp_path: Path,
) -> None:
    upstream = tmp_path / "events.tsv"
    content = b"onset\tduration\n0\t0\n"
    upstream.write_bytes(content)
    source = SourceSpec(
        dataset_id="example",
        provider="fixture",
        url="https://example.test/dataset",
        version="1.0.0",
        primary_path="events.tsv",
        files=(
            SourceFileSpec(
                path="events.tsv",
                url=upstream.as_uri(),
                checksum_algorithm="git",
                checksum=_git_digest(content),
            ),
        ),
    )

    snapshot = acquire_source(source, tmp_path / "cache")

    assert snapshot.path.read_bytes() == content
    assert snapshot.files[0]["checksum_algorithm"] == "git"
