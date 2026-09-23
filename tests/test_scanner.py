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


def test_scan_projects_collects_every_instruction_file(fake_root: Path) -> None:
    (fake_root / "project-b" / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (fake_root / "project-b" / "CLAUDE.local.md").write_text("# Mine\n", encoding="utf-8")
    nested = fake_root / "project-b" / "pkg" / "AGENTS.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Nested agents\n", encoding="utf-8")

    arcs = _arcnames(scanner.scan_projects(fake_root))
    assert "projects/project-b/AGENTS.md" in arcs
    assert "projects/project-b/CLAUDE.local.md" in arcs
    assert "projects/project-b/pkg/AGENTS.md" in arcs


def test_scan_global_collects_rules_but_not_plugins(fake_global: Path) -> None:
    for rel in (
        "rules/style.md",
        "plugins/installed_plugins.json",
        "plugins/known_marketplaces.json",
        "plugins/cache/mkt/plugin/1.0.0/SKILL.md",
        "plugins/data/some-plugin/token.json",
    ):
        path = fake_global / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")

    arcs = _arcnames(scanner.scan_global(fake_global))
    assert "global/rules/style.md" in arcs
    assert not any(a.startswith("global/plugins/") for a in arcs)


def test_scan_projects_skips_claude_worktrees(fake_root: Path) -> None:
    """.claude/worktrees/ holds full checkouts (and copied .env files) made
    by `claude --worktree`, never configuration."""
    wt = fake_root / "project-b" / ".claude" / "worktrees" / "feature"
    (wt / "src").mkdir(parents=True)
    (wt / "CLAUDE.md").write_text("# copy\n", encoding="utf-8")
    (wt / "src" / "main.py").write_text("print(1)\n", encoding="utf-8")
    # A skill that happens to be named "worktrees" is still configuration.
    skill = fake_root / "project-b" / ".claude" / "skills" / "worktrees" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("skill\n", encoding="utf-8")

    arcs = _arcnames(scanner.scan_projects(fake_root))
    assert not any("/.claude/worktrees/" in a for a in arcs)
    assert "projects/project-b/.claude/skills/worktrees/SKILL.md" in arcs


def test_env_variants_are_secrets(fake_root: Path, fake_global: Path) -> None:
    for path in (
        fake_root / "project-a" / ".claude" / "hooks" / ".env.local",
        fake_global / "skills" / "writer" / ".env.production",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("TOKEN=x\n", encoding="utf-8")

    arcs = _arcnames(scanner.scan_projects(fake_root) + scanner.scan_global(fake_global))
    assert not any(".env" in a for a in arcs)


def test_scan_global_collects_documented_personal_dirs(fake_global: Path) -> None:
    for rel in (
        "output-styles/terse.md",
        "workflows/review.js",
        "agent-memory/reviewer/MEMORY.md",
        "themes/dracula.json",
    ):
        path = fake_global / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")

    arcs = _arcnames(scanner.scan_global(fake_global))
    for rel in ("output-styles/terse.md", "workflows/review.js",
                "agent-memory/reviewer/MEMORY.md", "themes/dracula.json"):
        assert f"global/{rel}" in arcs
