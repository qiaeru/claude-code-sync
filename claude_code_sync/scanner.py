"""Discover the files to export, for both the project and global scopes.

The scanner is pure: it only reads the filesystem and returns a list of
:class:`Entry` objects mapping a source file on disk to its path inside the
archive. Nothing is written here.

Collection rules come from a :class:`~claude_code_sync.config.ScanConfig`, which
defaults to the built-in lists but can be extended by a ``.claude-code-sync.toml``
file in the scanned root.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from . import config
from .config import ScanConfig


@dataclass(frozen=True)
class Entry:
    """A single file to add to (or restore from) an archive.

    Attributes:
        source: Absolute path of the file on disk.
        arcname: POSIX-style path inside the archive (forward slashes).
        scope: Either ``"projects"`` or ``"global"``.
    """

    source: Path
    arcname: str
    scope: str


def _iter_files_pruned(base: Path, cfg: ScanConfig) -> Iterator[Path]:
    """Yield every file under *base*, skipping ``cfg.prune_dirs``."""
    for dirpath, dirnames, filenames in os.walk(base, followlinks=cfg.follow_symlinks):
        # Prune in-place so os.walk does not descend into noisy directories.
        dirnames[:] = [d for d in dirnames if d not in cfg.prune_dirs]
        current = Path(dirpath)
        for name in filenames:
            path = current / name
            # When not following symlinks, skip symlinked files too: os.walk
            # already declines to descend symlinked *directories*, so reading a
            # symlinked file would be inconsistent and could export data from
            # outside the scanned tree (e.g. CLAUDE.md -> /etc/passwd).
            if not cfg.follow_symlinks and path.is_symlink():
                continue
            yield path


def _arc(prefix: str, *parts: str) -> str:
    """Join archive path parts with forward slashes."""
    return "/".join((prefix, *parts))


def scan_projects(root: Path, cfg: ScanConfig | None = None) -> list[Entry]:
    """Collect Claude Code config from every project under *root*.

    For each direct sub-directory of *root* (except this tool's own folder) we
    collect:

    * every ``CLAUDE.md`` at any depth, and
    * the whole ``.claude/`` directory, minus machine-specific/secret files.
    """
    root = root.resolve()
    cfg = cfg or ScanConfig.load(root)
    self_name = config.tool_dir_name()
    entries: list[Entry] = []

    for project in sorted(p for p in root.iterdir() if p.is_dir()):
        if project.name == self_name or project.name in cfg.prune_dirs:
            continue
        entries.extend(_scan_one_project(root, project, cfg))

    return entries


def _scan_one_project(root: Path, project: Path, cfg: ScanConfig) -> Iterator[Entry]:
    # All CLAUDE.md files at any depth (pruning noisy directories). The project's
    # own .claude/ is pruned here because it is collected wholesale below; walking
    # it in both passes would double-traverse it and emit duplicate entries for
    # any CLAUDE.md living inside it.
    memory_cfg = cfg.with_pruned(cfg.claude_dir)
    for path in _iter_files_pruned(project, memory_cfg):
        if path.name != cfg.memory_file:
            continue
        rel = path.relative_to(root).as_posix()
        yield Entry(path, _arc(config.ARCHIVE_PROJECTS_PREFIX, rel), config.SCOPE_PROJECTS)

    claude_dir = project / cfg.claude_dir
    if claude_dir.is_dir():
        for path in _iter_files_pruned(claude_dir, cfg):
            rel_to_claude = path.relative_to(claude_dir)
            if _project_claude_excluded(rel_to_claude, cfg):
                continue
            rel = path.relative_to(root).as_posix()
            yield Entry(path, _arc(config.ARCHIVE_PROJECTS_PREFIX, rel), config.SCOPE_PROJECTS)


def _project_claude_excluded(rel_to_claude: Path, cfg: ScanConfig) -> bool:
    """True if a path inside a project ``.claude/`` must be skipped."""
    if cfg.is_secret(rel_to_claude.name):
        return True
    return any(part in cfg.project_claude_exclude for part in rel_to_claude.parts)


def scan_global(home_claude: Path | None = None, cfg: ScanConfig | None = None) -> list[Entry]:
    """Collect the allowed files from the global ``~/.claude`` directory.

    Uses an allow list (``cfg.global_include_*``) so secrets are never captured.
    *home_claude* defaults to ``~/.claude`` and is overridable for tests.
    """
    base = (home_claude or config.global_claude_dir()).resolve()
    cfg = cfg or ScanConfig.default()
    entries: list[Entry] = []
    if not base.is_dir():
        return entries

    for name in cfg.global_include_files:
        path = base / name
        if path.is_file() and not cfg.is_secret(path.name):
            entries.append(
                Entry(path, _arc(config.ARCHIVE_GLOBAL_PREFIX, name), config.SCOPE_GLOBAL)
            )

    for name in cfg.global_include_dirs:
        directory = base / name
        if not directory.is_dir():
            continue
        for path in _iter_files_pruned(directory, cfg):
            if cfg.is_secret(path.name):
                continue
            rel = path.relative_to(base).as_posix()
            entries.append(
                Entry(path, _arc(config.ARCHIVE_GLOBAL_PREFIX, rel), config.SCOPE_GLOBAL)
            )

    return entries


def scan(
    root: Path,
    scope: str,
    home_claude: Path | None = None,
    cfg: ScanConfig | None = None,
) -> list[Entry]:
    """Collect entries for the requested *scope* (``all``/``projects``/``global``)."""
    if scope not in config.VALID_SCOPES:
        raise ValueError(f"Invalid scope {scope!r}; expected one of {config.VALID_SCOPES}")

    cfg = cfg or ScanConfig.load(Path(root))
    entries: list[Entry] = []
    if scope in (config.SCOPE_ALL, config.SCOPE_PROJECTS):
        entries.extend(scan_projects(root, cfg))
    if scope in (config.SCOPE_ALL, config.SCOPE_GLOBAL):
        entries.extend(scan_global(home_claude, cfg))
    return entries


def total_size(entries: Iterable[Entry]) -> int:
    """Sum the byte size of all *entries* (best effort)."""
    total = 0
    for entry in entries:
        with contextlib.suppress(OSError):
            total += entry.source.stat().st_size
    return total
