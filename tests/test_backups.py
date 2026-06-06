"""Tests for backup listing/pruning, export retention, and their API handlers."""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_code_sync import api, archive, backups, config


def _make_backup(root: Path, name: str, files: dict[str, str]) -> Path:
    d = root / name
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


def test_list_backups_empty_when_missing(tmp_path: Path) -> None:
    assert backups.list_backups(tmp_path / "nope") == []


def test_list_backups_newest_first_with_stats(tmp_path: Path) -> None:
    _make_backup(tmp_path, "20240101-000000", {"a.txt": "aa"})
    _make_backup(tmp_path, "20240301-000000", {"b.txt": "bbb", "c/d.txt": "d"})

    infos = backups.list_backups(tmp_path)

    assert [b.name for b in infos] == ["20240301-000000", "20240101-000000"]
    newest = infos[0]
    assert newest.files == 2
    assert newest.size == len("bbb") + len("d")


def test_prune_backups_keeps_newest(tmp_path: Path) -> None:
    for name in ("20240101-000000", "20240201-000000", "20240301-000000"):
        _make_backup(tmp_path, name, {"f.txt": "x"})

    result = backups.prune_backups(1, root=tmp_path)

    assert [b.name for b in result.kept] == ["20240301-000000"]
    assert {b.name for b in result.removed} == {"20240101-000000", "20240201-000000"}
    assert (tmp_path / "20240301-000000").is_dir()
    assert not (tmp_path / "20240101-000000").exists()


def test_prune_backups_dry_run_deletes_nothing(tmp_path: Path) -> None:
    _make_backup(tmp_path, "20240101-000000", {"f.txt": "x"})
    _make_backup(tmp_path, "20240201-000000", {"f.txt": "x"})

    result = backups.prune_backups(1, root=tmp_path, dry_run=True)

    assert result.dry_run is True
    assert len(result.removed) == 1
    assert (tmp_path / "20240101-000000").is_dir()  # untouched


def test_prune_backups_rejects_negative(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        backups.prune_backups(-1, root=tmp_path)


def test_prune_archives_keeps_newest_by_mtime(tmp_path: Path) -> None:
    # Different hostnames, so a name sort would be wrong; mtime must win.
    old = tmp_path / "claude-code-sync-zzz-20200101-000000.zip"
    new = tmp_path / "claude-code-sync-aaa-20990101-000000.zip"
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    import os

    os.utime(old, (1_000_000_000, 1_000_000_000))
    os.utime(new, (2_000_000_000, 2_000_000_000))

    removed = archive.prune_archives(tmp_path, keep=1)

    assert removed == [old]
    assert new.is_file()
    assert not old.exists()


def test_handle_list_and_prune_backups(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "backup_root", lambda: tmp_path)
    for name in ("20240101-000000", "20240201-000000", "20240301-000000"):
        _make_backup(tmp_path, name, {"f.txt": "x"})

    listed = api.handle_list_backups()
    assert listed["count"] == 3
    assert listed["root"] == str(tmp_path)

    preview = api.handle_prune_backups({"keep": 1, "dry_run": True})
    assert preview["removed"] == 2
    assert (tmp_path / "20240101-000000").is_dir()  # dry run kept it

    done = api.handle_prune_backups({"keep": 1})
    assert done["removed"] == 2
    assert done["kept"] == 1
    assert not (tmp_path / "20240101-000000").exists()


def test_handle_prune_backups_validates_keep(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "backup_root", lambda: tmp_path)
    with pytest.raises(api.ApiError):
        api.handle_prune_backups({})  # missing keep
    with pytest.raises(api.ApiError):
        api.handle_prune_backups({"keep": "lots"})  # not an integer


def test_handle_export_keep_prunes_old_archives(fake_root: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Pre-existing older archives that retention should remove.
    for i in range(3):
        (out_dir / f"claude-code-sync-host-2020010{i}-000000.zip").write_bytes(b"old")

    result = api.handle_export(
        {
            "root": str(fake_root),
            "scope": "projects",
            "out_dir": str(out_dir),
            "password": "pw",
            "keep": 1,
        }
    )

    assert result.get("pruned", 0) >= 1
    # Only the freshly created archive remains.
    remaining = list(out_dir.glob(config.ARCHIVE_GLOB))
    assert len(remaining) == 1
    assert remaining[0].name == Path(result["archive"]).name
