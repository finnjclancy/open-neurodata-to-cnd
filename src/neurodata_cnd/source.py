"""Pinned, checksum-verified source acquisition."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .recipe import SourceSpec


class SourceIntegrityError(RuntimeError):
    """A source file does not match its reviewed recipe."""


@dataclass(slots=True, frozen=True)
class SourceSnapshot:
    path: Path
    root: Path
    sha256: str
    size_bytes: int
    reused_cache: bool
    files: tuple[dict[str, str | int], ...]


def sha256_file(path: str | Path) -> str:
    """Return a streaming SHA-256 digest without loading the file into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def acquire_source(
    source: SourceSpec,
    cache_root: str | Path,
    *,
    source_override: str | Path | None = None,
) -> SourceSnapshot:
    """Resolve a local override or atomically download one pinned source file."""
    if source_override is not None:
        if len(source.files) != 1:
            raise ValueError("A single-file source override cannot replace a file set")
        path = Path(source_override).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        source_file = source.files[0]
        _verify(path, source_file.sha256)
        record = _record(source_file.path, path, source_file.sha256)
        return SourceSnapshot(
            path,
            path.parent,
            _snapshot_digest((record,)),
            path.stat().st_size,
            True,
            (record,),
        )

    snapshot_root = (
        Path(cache_root).expanduser().resolve() / source.dataset_id / source.version
    )
    records: list[dict[str, str | int]] = []
    reused_all = True
    for source_file in source.files:
        destination = snapshot_root / source_file.path
        if destination.is_file():
            _verify(destination, source_file.sha256)
        else:
            reused_all = False
            _download(source_file.url, destination, source_file.sha256)
        records.append(_record(source_file.path, destination, source_file.sha256))
    primary = snapshot_root / source.primary_path
    record_tuple = tuple(records)
    return SourceSnapshot(
        primary,
        snapshot_root,
        _snapshot_digest(record_tuple),
        sum(int(record["size_bytes"]) for record in records),
        reused_all,
        record_tuple,
    )


def _download(url: str, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".download", dir=destination.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "open-neurodata-to-cnd/0.1"}
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            with temporary.open("wb") as handle:
                while block := response.read(1024 * 1024):
                    handle.write(block)
        _verify(temporary, expected_sha256)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _record(path: str, local_path: Path, digest: str) -> dict[str, str | int]:
    return {"path": path, "size_bytes": local_path.stat().st_size, "sha256": digest}


def _snapshot_digest(records: tuple[dict[str, str | int], ...]) -> str:
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify(path: Path, expected: str) -> None:
    observed = sha256_file(path)
    if observed != expected:
        raise SourceIntegrityError(
            f"SHA-256 mismatch for {path}: expected {expected}, observed {observed}"
        )
