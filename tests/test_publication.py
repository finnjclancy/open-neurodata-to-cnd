from pathlib import Path

import pytest

from neurodata_cnd.publication import staged_directory


def test_failed_build_keeps_existing_release(tmp_path):
    destination = tmp_path / "release"
    destination.mkdir()
    (destination / "value").write_text("old")
    with pytest.raises(RuntimeError, match="failed check"):
        with staged_directory(destination, overwrite=True) as staging:
            (staging / "value").write_text("new")
            raise RuntimeError("failed check")
    assert (destination / "value").read_text() == "old"
    assert list(tmp_path.iterdir()) == [destination]


def test_failed_publish_restores_existing_release(tmp_path, monkeypatch):
    destination = tmp_path / "release"
    destination.mkdir()
    (destination / "value").write_text("old")
    rename = Path.rename

    def fail_staging_move(path, target):
        if ".staging-" in path.name:
            raise OSError("publish failed")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_staging_move)
    with pytest.raises(OSError, match="publish failed"):
        with staged_directory(destination, overwrite=True) as staging:
            (staging / "value").write_text("new")
    assert (destination / "value").read_text() == "old"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("blocked_by", ["existing_release", "existing_backup"])
def test_publish_refuses_conflicts(tmp_path, blocked_by):
    destination = tmp_path / "release"
    destination.mkdir()
    (destination / "value").write_text("old")
    backup = tmp_path / ".release.backup"
    if blocked_by == "existing_backup":
        backup.mkdir()
        (backup / "value").write_text("recoverable")
    with pytest.raises(FileExistsError):
        with staged_directory(
            destination, overwrite=blocked_by == "existing_backup"
        ) as staging:
            (staging / "value").write_text("new")
    assert (destination / "value").read_text() == "old"
    assert not list(tmp_path.glob("*.staging-*"))
    if backup.exists():
        assert (backup / "value").read_text() == "recoverable"


def test_successful_publish_replaces_complete_release(tmp_path):
    destination = tmp_path / "release"
    destination.mkdir()
    (destination / "old").write_text("old")
    with staged_directory(destination, overwrite=True) as staging:
        (staging / "new").write_text("new")
    assert (destination / "new").read_text() == "new"
    assert not (destination / "old").exists()
    assert list(tmp_path.iterdir()) == [destination]
