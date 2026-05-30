"""Selective export/import: only chosen files are archived/restored."""

from __future__ import annotations

from pathlib import Path

from claude_code_sync import api, archive, config, importer, scanner


def test_export_honours_selection(fake_root: Path, tmp_path: Path) -> None:
    entries = scanner.scan_projects(fake_root)
    chosen = entries[0].arcname

    result = api.handle_export(
        {
            "root": str(fake_root),
            "scope": config.SCOPE_PROJECTS,
            "out_dir": str(tmp_path),
            "password": "pw",
            "selection": [chosen],
        }
    )
    man = archive.read_manifest(Path(result["archive"]), "pw")
    arcs = [e["arcname"] for e in man["entries"]]
    assert arcs == [chosen]


def test_import_honours_selection(fake_root: Path, tmp_path: Path) -> None:
    entries = scanner.scan_projects(fake_root)
    out = tmp_path / "bundle.zip"
    archive.create(entries, out, "pw", config.SCOPE_PROJECTS)

    chosen = entries[0].arcname
    target = tmp_path / "restore"
    result = importer.run_import(
        out, "pw", target,
        scope=config.SCOPE_PROJECTS, home_claude=tmp_path / "home",
        backup_root=tmp_path / "bk", selection=[chosen],
    )

    assert result.created == 1
    assert result.skipped == len(entries) - 1
    created = [i.arcname for i in result.items if i.action.value == "create"]
    assert created == [chosen]
