"""Tests for the optional .claude-code-sync.toml configuration file."""

from __future__ import annotations

import sys
from pathlib import Path

from claude_code_sync import config, scanner
from claude_code_sync.config import ScanConfig


def test_default_config_matches_constants() -> None:
    cfg = ScanConfig.default()
    assert "node_modules" in cfg.prune_dirs
    assert "settings.json" in cfg.global_include_files
    assert cfg.follow_symlinks is False


def test_toml_extends_lists(tmp_path: Path) -> None:
    (tmp_path / ".claude-code-sync.toml").write_text(
        """
        [scan]
        prune_dirs = ["coverage_html"]
        follow_symlinks = true

        [project]
        exclude = ["local.json"]

        [global]
        include_files = ["mcp.json"]
        include_dirs = ["prompts"]

        [secrets]
        names = ["token.txt"]
        """,
        encoding="utf-8",
    )
    cfg = ScanConfig.load(tmp_path)

    assert "coverage_html" in cfg.prune_dirs and "node_modules" in cfg.prune_dirs  # extends
    assert "local.json" in cfg.project_claude_exclude
    assert "mcp.json" in cfg.global_include_files
    assert "prompts" in cfg.global_include_dirs
    assert cfg.is_secret("token.txt")
    assert cfg.follow_symlinks is True


def test_scanner_respects_config_file(tmp_path: Path) -> None:
    root = tmp_path / "GitHub"
    proj = root / "proj"
    (proj / "coverage_html").mkdir(parents=True)
    (proj / "coverage_html" / "CLAUDE.md").write_text("should be pruned\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("kept\n", encoding="utf-8")
    (root / ".claude-code-sync.toml").write_text(
        '[scan]\nprune_dirs = ["coverage_html"]\n', encoding="utf-8"
    )

    arcs = {e.arcname for e in scanner.scan_projects(root)}
    assert "projects/proj/CLAUDE.md" in arcs
    assert not any("coverage_html" in a for a in arcs)


def test_default_root_from_source_checkout() -> None:
    checkout = Path(config.__file__).resolve().parent.parent
    assert config.default_root() == checkout.parent
    assert config.tool_dir_name() == checkout.name


def test_default_root_when_installed_is_cwd(tmp_path: Path, monkeypatch) -> None:
    """An installed copy must not scan the folder around site-packages."""
    fake = tmp_path / "site-packages" / "claude_code_sync" / "config.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("", encoding="utf-8")
    monkeypatch.setattr(config, "__file__", str(fake))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    assert config.default_root() == work.resolve()
    assert config.tool_dir_name() == ""


def test_default_root_when_frozen_is_executable_dir(tmp_path: Path, monkeypatch) -> None:
    exe = tmp_path / "GitHub" / "claude-code-sync.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))

    assert config.default_root() == exe.parent.resolve()
    assert config.tool_dir_name() == ""


def test_secret_names_also_exclude_instruction_files(tmp_path: Path) -> None:
    """secrets.names must reach CLAUDE.local.md, or it cannot be kept out."""
    root = tmp_path / "GitHub"
    (root / "proj").mkdir(parents=True)
    (root / "proj" / "CLAUDE.md").write_text("shared", encoding="utf-8")
    (root / "proj" / "CLAUDE.local.md").write_text("private", encoding="utf-8")
    (root / ".claude-code-sync.toml").write_text(
        '[secrets]' + chr(10) + 'names = ["CLAUDE.local.md"]' + chr(10), encoding="utf-8"
    )

    arcs = {e.arcname for e in scanner.scan_projects(root)}
    assert "projects/proj/CLAUDE.md" in arcs
    assert "projects/proj/CLAUDE.local.md" not in arcs
