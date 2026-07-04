"""Headless CLI: export then import round-trip via the command line."""

from __future__ import annotations

from pathlib import Path

from claude_code_sync.__main__ import main


def test_cli_export_then_import(fake_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "cli-secret")
    out_dir = tmp_path / "out"

    rc = main(
        ["export", "--root", str(fake_root), "--scope", "projects", "--out-dir", str(out_dir)]
    )
    assert rc == 0
    archives = list(out_dir.glob("*.zip"))
    assert len(archives) == 1

    target = tmp_path / "restored"
    rc = main(
        ["import", str(archives[0]), "--root", str(target), "--scope", "projects", "--yes"]
    )
    assert rc == 0
    assert (target / "project-a" / "CLAUDE.md").is_file()


def test_cli_export_keep_prunes_old_archives(fake_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "cli-secret")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    for i in range(3):
        (out_dir / f"claude-code-sync-host-2020010{i}-000000.zip").write_bytes(b"old")

    rc = main(
        ["export", "--root", str(fake_root), "--scope", "projects",
         "--out-dir", str(out_dir), "--keep", "1"]
    )
    assert rc == 0
    assert len(list(out_dir.glob("*.zip"))) == 1


def test_cli_import_dry_run_writes_nothing(fake_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "cli-secret")
    out_dir = tmp_path / "out"
    main(["export", "--root", str(fake_root), "--scope", "projects", "--out-dir", str(out_dir)])
    archive_path = next(out_dir.glob("*.zip"))

    target = tmp_path / "restored"
    rc = main(["import", str(archive_path), "--root", str(target), "--dry-run"])
    assert rc == 0
    assert not target.exists()


def test_cli_inspect_lists_manifest(fake_root: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "cli-secret")
    out_dir = tmp_path / "out"
    main(["export", "--root", str(fake_root), "--scope", "projects", "--out-dir", str(out_dir)])
    archive_path = next(out_dir.glob("*.zip"))

    rc = main(["inspect", str(archive_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "projects/project-a/CLAUDE.md" in out
    assert "Scope:   projects" in out


def test_cli_inspect_rejects_wrong_password(
    fake_root: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "cli-secret")
    out_dir = tmp_path / "out"
    main(["export", "--root", str(fake_root), "--scope", "projects", "--out-dir", str(out_dir)])
    archive_path = next(out_dir.glob("*.zip"))

    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "wrong")
    rc = main(["inspect", str(archive_path)])
    assert rc == 1


def _seed_backups(root: Path, count: int) -> None:
    for i in range(count):
        d = root / f"2026010{i + 1}-000000"
        d.mkdir(parents=True)
        (d / "file.txt").write_text("x", encoding="utf-8")


def test_cli_backups_list_and_prune(tmp_path: Path, monkeypatch, capsys) -> None:
    backup_root = tmp_path / "bk"
    _seed_backups(backup_root, 3)
    monkeypatch.setattr("claude_code_sync.config.backup_root", lambda: backup_root)

    rc = main(["backups", "list"])
    assert rc == 0
    assert "3 backup(s)" in capsys.readouterr().out

    rc = main(["backups", "prune", "--keep", "1"])
    assert rc == 0
    remaining = [p.name for p in backup_root.iterdir()]
    assert remaining == ["20260103-000000"]  # the newest one


def test_cli_backups_prune_dry_run_deletes_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    backup_root = tmp_path / "bk"
    _seed_backups(backup_root, 2)
    monkeypatch.setattr("claude_code_sync.config.backup_root", lambda: backup_root)

    rc = main(["backups", "prune", "--keep", "0", "--dry-run"])
    assert rc == 0
    assert "Would remove 2" in capsys.readouterr().out
    assert len(list(backup_root.iterdir())) == 2
