"""Scanner tests: correct collection and strict exclusion of secrets/noise."""

from __future__ import annotations

from pathlib import Path

from claude_code_sync import config, scanner


def _arcnames(entries) -> set[str]:
    return {e.arcname for e in entries}


def test_scan_projects_collects_memory_and_claude_dir(fake_root: Path) -> None:
    arcs = _arcnames(scanner.scan_projects(fake_root))

    assert "projects/project-a/CLAUDE.md" in arcs
    assert "projects/project-a/src/CLAUDE.md" in arcs
    assert "projects/project-a/.claude/settings.json" in arcs
    assert "projects/project-a/.claude/skills/demo/SKILL.md" in arcs
    assert "projects/project-b/CLAUDE.md" in arcs
    assert "projects/project-b/.claude/agents/helper.md" in arcs


def test_scan_projects_no_duplicate_arcnames(fake_root: Path) -> None:
    entries = scanner.scan_projects(fake_root)
    arcs = [e.arcname for e in entries]

    # A CLAUDE.md inside .claude/ must appear exactly once, not twice.
    assert "projects/project-a/.claude/CLAUDE.md" in arcs
    assert len(arcs) == len(set(arcs)), "duplicate arcnames were emitted"


def test_scan_projects_excludes_secrets_and_noise(fake_root: Path) -> None:
    arcs = _arcnames(scanner.scan_projects(fake_root))

    # Machine-specific and secret files inside .claude must be excluded.
    assert "projects/project-a/.claude/settings.local.json" not in arcs
    assert "projects/project-a/.claude/.credentials.json" not in arcs
    # Pruned directories must not be walked.
    assert not any("node_modules" in a for a in arcs)


def test_scan_global_uses_allow_list(fake_global: Path) -> None:
    arcs = _arcnames(scanner.scan_global(fake_global))

    assert "global/settings.json" in arcs
    assert "global/keybindings.json" in arcs
    assert "global/CLAUDE.md" in arcs
    assert "global/skills/writer/SKILL.md" in arcs


def test_scan_global_never_exports_secrets(fake_global: Path) -> None:
    arcs = _arcnames(scanner.scan_global(fake_global))

    forbidden = (".credentials.json", "todos/", "projects/", "settings.local.json")
    for needle in forbidden:
        assert not any(needle in a for a in arcs), f"{needle} leaked into archive"


def test_scan_all_combines_scopes(fake_root: Path, fake_global: Path) -> None:
    entries = scanner.scan(fake_root, config.SCOPE_ALL, home_claude=fake_global)
    scopes = {e.scope for e in entries}
    assert scopes == {config.SCOPE_PROJECTS, config.SCOPE_GLOBAL}
