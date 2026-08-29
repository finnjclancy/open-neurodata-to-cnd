"""Pinned, checksum-verified source acquisition."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import urllib.error
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
        algorithm, checksum = source_file.integrity
        _verify(path, algorithm, checksum)
        record = _record(source_file.path, path, algorithm, checksum)
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
        algorithm, checksum = source_file.integrity
        if destination.is_file():
            _verify(destination, algorithm, checksum)
        else:
            reused_all = False
            _download(source_file.url, destination, algorithm, checksum)
        records.append(_record(source_file.path, destination, algorithm, checksum))
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


def remove_snapshot_files(snapshot: SourceSnapshot, paths: set[str]) -> int:
    """Remove selected verified source files and now-empty subject directories."""
    declared = {str(record["path"]) for record in snapshot.files}
    unknown = paths - declared
    if unknown:
        raise ValueError(f"Cannot remove undeclared snapshot paths: {sorted(unknown)}")
    removed = 0
    for relative in sorted(paths, reverse=True):
        target = snapshot.root / relative
        if target.is_file():
            target.unlink()
            removed += 1
        parent = target.parent
        while parent != snapshot.root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return removed


def remove_cached_source_files(
    source: SourceSpec, cache_root: str | Path, paths: set[str]
) -> int:
    """Remove exact declared cache files after a successfully published job."""
    declared = {item.path for item in source.files}
    unknown = paths - declared
    if unknown:
        raise ValueError(f"Cannot remove undeclared source paths: {sorted(unknown)}")
    root = Path(cache_root).expanduser().resolve() / source.dataset_id / source.version
    records: tuple[dict[str, str | int], ...] = tuple(
        {"path": path} for path in sorted(declared)
    )
    snapshot = SourceSnapshot(root, root, "", 0, True, records)
    return remove_snapshot_files(snapshot, paths)


def _download(
    url: str, destination: Path, algorithm: str, expected_checksum: str
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".download", dir=destination.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        for attempt in range(1, 5):
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "open-neurodata-to-cnd/0.2"}
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    with temporary.open("wb") as handle:
                        while block := response.read(1024 * 1024):
                            handle.write(block)
                break
            except (TimeoutError, urllib.error.URLError, ConnectionError):
                if attempt == 4:
                    raise
                time.sleep(2 ** (attempt - 1))
        _verify(temporary, algorithm, expected_checksum)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _record(
    path: str, local_path: Path, algorithm: str, digest: str
) -> dict[str, str | int]:
    if algorithm == "sha256":
        return {
            "path": path,
            "size_bytes": local_path.stat().st_size,
            "sha256": digest,
        }
    return {
        "path": path,
        "size_bytes": local_path.stat().st_size,
        "checksum_algorithm": algorithm,
        "checksum": digest,
    }


def _snapshot_digest(records: tuple[dict[str, str | int], ...]) -> str:
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify(path: Path, algorithm: str, expected: str) -> None:
    if algorithm == "sha256":
        observed = sha256_file(path)
    elif algorithm == "git":
        digest = hashlib.sha1(usedforsecurity=False)
        digest.update(f"blob {path.stat().st_size}\0".encode())
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        observed = digest.hexdigest()
    else:
        raise ValueError(f"Unsupported checksum algorithm {algorithm!r}")
    if observed != expected:
        label = "SHA-256" if algorithm == "sha256" else algorithm
        raise SourceIntegrityError(
            f"{label} mismatch for {path}: expected {expected}, observed {observed}"
        )
