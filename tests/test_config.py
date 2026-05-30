"""Tests for the optional .claude-code-sync.toml configuration file."""

from __future__ import annotations

from pathlib import Path

from claude_code_sync import scanner
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
