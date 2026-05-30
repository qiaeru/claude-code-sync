"""End-to-end: export -> encrypted archive -> import, with backups and secrets."""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_code_sync import archive, config, importer, scanner


def _export(root: Path, global_dir: Path, out: Path, password: str) -> Path:
    entries = scanner.scan_projects(root) + scanner.scan_global(global_dir)
    return archive.create(entries, out, password, config.SCOPE_ALL)


def test_export_creates_encrypted_archive(fake_root, fake_global, tmp_path) -> None:
    out = tmp_path / "bundle.zip"
    _export(fake_root, fake_global, out, "s3cret")
    assert out.is_file()

    # Wrong password must fail, correct one must succeed.
    with pytest.raises(archive.BadPassword):
        archive.read_manifest(out, "wrong")
    man = archive.read_manifest(out, "s3cret")
    assert man["format_version"] == config.ARCHIVE_VERSION
    assert man["entry_count"] > 0


def test_no_secret_is_ever_archived(fake_root, fake_global, tmp_path) -> None:
    out = tmp_path / "bundle.zip"
    _export(fake_root, fake_global, out, "pw")
    man = archive.read_manifest(out, "pw")
    arcs = [e["arcname"] for e in man["entries"]]

    for arc in arcs:
        assert ".credentials.json" not in arc
        assert "settings.local.json" not in arc
        assert "/todos/" not in arc


def test_roundtrip_restores_identical_content(fake_root, fake_global, tmp_path) -> None:
    out = tmp_path / "bundle.zip"
    _export(fake_root, fake_global, out, "pw")

    target_root = tmp_path / "restored_projects"
    target_global = tmp_path / "restored_global"
    backup_root = tmp_path / "backups"

    result = importer.run_import(
        out, "pw", target_root,
        scope=config.SCOPE_ALL, home_claude=target_global, backup_root=backup_root,
    )
    assert not result.dry_run
    assert result.created > 0

    # A representative project file matches the original byte-for-byte.
    src = (fake_root / "project-a" / "src" / "CLAUDE.md").read_bytes()
    dst = (target_root / "project-a" / "src" / "CLAUDE.md").read_bytes()
    assert src == dst

    # A global file landed in the target ~/.claude.
    assert (target_global / "settings.json").read_text() == '{"theme": "dark"}\n'


def test_dry_run_writes_nothing(fake_root, fake_global, tmp_path) -> None:
    out = tmp_path / "bundle.zip"
    _export(fake_root, fake_global, out, "pw")

    target_root = tmp_path / "restored"
    target_global = tmp_path / "restored_global"
    result = importer.run_import(
        out, "pw", target_root,
        scope=config.SCOPE_ALL, home_claude=target_global, dry_run=True,
    )
    assert result.dry_run
    assert result.created > 0
    assert not target_root.exists()
    assert not target_global.exists()


def test_import_backs_up_existing_files(fake_root, fake_global, tmp_path) -> None:
    out = tmp_path / "bundle.zip"
    _export(fake_root, fake_global, out, "pw")

    target_root = tmp_path / "restored"
    target_global = tmp_path / "restored_global"
    backup_root = tmp_path / "backups"

    # Pre-existing file at a destination that the archive will overwrite.
    existing = target_root / "project-a" / "CLAUDE.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("OLD CONTENT\n", encoding="utf-8")

    result = importer.run_import(
        out, "pw", target_root,
        scope=config.SCOPE_ALL, home_claude=target_global, backup_root=backup_root,
    )

    assert result.overwritten >= 1
    assert result.backup_dir is not None
    # The old content is preserved somewhere under the backup dir.
    backups = list(Path(result.backup_dir).rglob("CLAUDE.md"))
    assert any(b.read_text() == "OLD CONTENT\n" for b in backups)
    # And the destination now holds the restored content.
    assert existing.read_text() == "# Project A memory\n"


def test_scope_filtering_on_import(fake_root, fake_global, tmp_path) -> None:
    out = tmp_path / "bundle.zip"
    _export(fake_root, fake_global, out, "pw")

    target_root = tmp_path / "restored"
    target_global = tmp_path / "restored_global"
    result = importer.run_import(
        out, "pw", target_root,
        scope=config.SCOPE_PROJECTS, home_claude=target_global,
        backup_root=tmp_path / "b",
    )
    # Global entries are skipped, so nothing lands in the global target.
    assert result.skipped > 0
    assert not target_global.exists()
