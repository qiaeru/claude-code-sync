"""List and prune the import backups created during a restore.

Each import copies the files it is about to overwrite into a timestamped folder
under ``~/.claude-code-sync-backups/`` (see :mod:`importer`). The tool never
removes them, so this module provides the housekeeping: report what is there and
keep only the newest few. It only ever touches that directory, so it cannot
affect repositories or live configuration.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import config


@dataclass(frozen=True)
class BackupInfo:
    """One timestamped backup directory and its aggregate size."""

    name: str
    path: Path
    size: int
    files: int
    mtime: float


@dataclass
class PruneResult:
    """Outcome of a prune (real or dry-run)."""

    removed: list[BackupInfo]
    kept: list[BackupInfo]
    dry_run: bool

    @property
    def freed(self) -> int:
        return sum(b.size for b in self.removed)


def _dir_stats(path: Path) -> tuple[int, int]:
    """Return ``(total_size_bytes, file_count)`` for everything under *path*."""
    size = 0
    files = 0
    for p in path.rglob("*"):
        if p.is_symlink() or not p.is_file():
            continue
        try:
            size += p.stat().st_size
        except OSError:
            continue
        files += 1
    return size, files


def list_backups(root: Path | None = None) -> list[BackupInfo]:
    """Return the backups under *root* (default ``~/.claude-code-sync-backups``).

    Newest first. The directory names are timestamps, so a reverse name sort is
    chronological. Returns an empty list if the directory does not exist.
    """
    base = Path(root) if root is not None else config.backup_root()
    if not base.is_dir():
        return []
    infos: list[BackupInfo] = []
    for child in base.iterdir():
        if child.is_symlink() or not child.is_dir():
            continue
        size, files = _dir_stats(child)
        try:
            mtime = child.stat().st_mtime
        except OSError:
            mtime = 0.0
        infos.append(BackupInfo(child.name, child, size, files, mtime))
    infos.sort(key=lambda b: b.name, reverse=True)
    return infos


def prune_backups(keep: int, root: Path | None = None, dry_run: bool = False) -> PruneResult:
    """Keep the newest *keep* backups under *root* and remove the rest.

    *keep* must be ``>= 0``. With *dry_run* nothing is deleted, but the split into
    kept/removed is still reported so callers can preview it.
    """
    if keep < 0:
        raise ValueError("keep must be >= 0")
    backups = list_backups(root)
    kept = backups[:keep]
    removed = backups[keep:]
    if not dry_run:
        for b in removed:
            shutil.rmtree(b.path, ignore_errors=True)
    return PruneResult(removed=removed, kept=kept, dry_run=dry_run)
