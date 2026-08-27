"""Pinned, checksum-verified source acquisition."""

from __future__ import annotations

import hashlib
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
    sha256: str
    size_bytes: int
    reused_cache: bool


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
        path = Path(source_override).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        _verify(path, source.sha256)
        return SourceSnapshot(path, source.sha256, path.stat().st_size, True)

    destination = (
        Path(cache_root).expanduser().resolve()
        / source.dataset_id
        / source.version
        / source.filename
    )
    if destination.is_file():
        _verify(destination, source.sha256)
        return SourceSnapshot(
            destination, source.sha256, destination.stat().st_size, True
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".download", dir=destination.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(
            source.file_url,
            headers={"User-Agent": "open-neurodata-to-cnd/0.1"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            with temporary.open("wb") as handle:
                while block := response.read(1024 * 1024):
                    handle.write(block)
        _verify(temporary, source.sha256)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return SourceSnapshot(destination, source.sha256, destination.stat().st_size, False)


def _verify(path: Path, expected: str) -> None:
    observed = sha256_file(path)
    if observed != expected:
        raise SourceIntegrityError(
            f"SHA-256 mismatch for {path}: expected {expected}, observed {observed}"
        )
