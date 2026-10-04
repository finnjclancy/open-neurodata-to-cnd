"""Publish a complete directory with rollback when replacement fails."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _new_staging_directory(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent)
    )


def _publish_staging(staging: Path, destination: Path, *, overwrite: bool) -> None:
    if not destination.exists():
        staging.rename(destination)
        return
    if not overwrite:
        raise FileExistsError(f"Refusing to overwrite {destination}")
    backup = destination.with_name(f".{destination.name}.backup")
    if backup.exists():
        raise FileExistsError(f"Cannot replace release while backup exists: {backup}")
    destination.rename(backup)
    try:
        staging.rename(destination)
    except BaseException:
        backup.rename(destination)
        raise
    else:
        shutil.rmtree(backup)


@contextmanager
def staged_directory(destination: Path, *, overwrite: bool) -> Iterator[Path]:
    """Publish after a successful build; discard staging on any failure."""
    staging = _new_staging_directory(destination)
    try:
        yield staging
        _publish_staging(staging, destination, overwrite=overwrite)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
