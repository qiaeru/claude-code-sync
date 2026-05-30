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


def test_cli_import_dry_run_writes_nothing(fake_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SYNC_PASSWORD", "cli-secret")
    out_dir = tmp_path / "out"
    main(["export", "--root", str(fake_root), "--scope", "projects", "--out-dir", str(out_dir)])
    archive_path = next(out_dir.glob("*.zip"))

    target = tmp_path / "restored"
    rc = main(["import", str(archive_path), "--root", str(target), "--dry-run"])
    assert rc == 0
    assert not target.exists()
