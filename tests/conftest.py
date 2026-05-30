"""Shared fixtures: build a fake projects root and a fake global ~/.claude."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    """A projects root with two projects, nested CLAUDE.md and .claude dirs.

    Also seeds machine-specific and secret files that must NOT be exported.
    """
    root = tmp_path / "GitHub"

    # Project A
    _write(root / "project-a" / "CLAUDE.md", "# Project A memory\n")
    _write(root / "project-a" / "src" / "CLAUDE.md", "# Nested memory\n")
    _write(root / "project-a" / ".claude" / "settings.json", '{"a": 1}\n')
    _write(root / "project-a" / ".claude" / "skills" / "demo" / "SKILL.md", "skill\n")
    # A CLAUDE.md living inside .claude/ must be collected exactly once (by the
    # .claude pass), not also by the memory-file walk.
    _write(root / "project-a" / ".claude" / "CLAUDE.md", "# In-claude memory\n")
    _write(root / "project-a" / ".claude" / "settings.local.json", '{"secret": true}\n')
    _write(root / "project-a" / ".claude" / ".credentials.json", '{"token": "x"}\n')
    # Noise that must be pruned.
    _write(root / "project-a" / "node_modules" / "pkg" / "CLAUDE.md", "should be skipped\n")

    # Project B
    _write(root / "project-b" / "CLAUDE.md", "# Project B memory\n")
    _write(root / "project-b" / ".claude" / "agents" / "helper.md", "agent\n")

    return root


@pytest.fixture
def fake_global(tmp_path: Path) -> Path:
    """A fake ~/.claude directory with allowed files and secrets to exclude."""
    home = tmp_path / "home_claude"
    _write(home / "settings.json", '{"theme": "dark"}\n')
    _write(home / "keybindings.json", '{"submit": "enter"}\n')
    _write(home / "CLAUDE.md", "# Global memory\n")
    _write(home / "skills" / "writer" / "SKILL.md", "global skill\n")
    # Secrets / noise that must never be exported.
    _write(home / ".credentials.json", '{"token": "secret"}\n')
    _write(home / "todos" / "today.json", "[]\n")
    _write(home / "projects" / "p" / "history.jsonl", "{}\n")
    _write(home / "settings.local.json", '{"machine": true}\n')
    return home
