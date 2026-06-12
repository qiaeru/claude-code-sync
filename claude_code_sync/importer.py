"""Restore an encrypted archive onto the current machine.

Destinations are derived from each archive member's prefix:

* ``global/<rel>``      -> ``~/.claude/<rel>``
* ``projects/<rel>``    -> ``<root>/<rel>``

Before any existing file is overwritten it is moved into a timestamped backup
directory (``~/.claude-code-sync-backups/<timestamp>/`` by default), preserving
its relative layout. A dry run reports the planned actions without touching disk.

Security: archive member names are validated before use. Any entry that tries to
escape its destination root (``..`` segments, absolute paths, drive letters) is
rejected, so a malicious archive cannot write outside the chosen folders.
Restored files are also checked against the SHA-256 recorded in the manifest.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from . import archive, config, manifest


class IntegrityError(Exception):
    """Raised when a restored file does not match its recorded checksum."""


class Action(StrEnum):
    """What will happen to a destination file."""

    CREATE = "create"  # destination does not exist yet
    OVERWRITE = "overwrite"  # destination exists and will be backed up first
    SKIP = "skip"  # filtered out by the requested scope or selection


@dataclass
class PlannedItem:
    """One restore action, used for both dry-run preview and reporting."""

    arcname: str
    scope: str
    destination: Path
    action: Action


@dataclass
class ImportResult:
    """Outcome of an import (dry-run or real)."""

    dry_run: bool
    scope: str
    items: list[PlannedItem]
    backup_dir: Path | None

    @property
    def created(self) -> int:
        return sum(1 for i in self.items if i.action is Action.CREATE)

    @property
    def overwritten(self) -> int:
        return sum(1 for i in self.items if i.action is Action.OVERWRITE)

    @property
    def skipped(self) -> int:
        return sum(1 for i in self.items if i.action is Action.SKIP)


def _safe_join(base: Path, parts: list[str]) -> Path | None:
    """Join *parts* under *base*, or return ``None`` if it would escape *base*.

    Rejects empty/``.``/``..`` segments, embedded separators, and any component
    that looks absolute or carries a drive/anchor.
    """
    for part in parts:
        if not part or part in (".", "..") or "/" in part or "\\" in part:
            return None
        p = Path(part)
        if p.is_absolute() or p.drive or p.anchor:
            return None
    candidate = base.joinpath(*parts)
    try:
        candidate.resolve().relative_to(base.resolve())
    except (ValueError, OSError):
        return None
    return candidate


def _destination_for(arcname: str, root: Path, home_claude: Path) -> tuple[str, Path] | None:
    """Map an *arcname* to ``(scope, destination_path)`` or ``None`` to ignore."""
    parts = arcname.split("/")
    if len(parts) < 2:
        return None
    prefix, rest = parts[0], parts[1:]
    if prefix == config.ARCHIVE_GLOBAL_PREFIX:
        dest = _safe_join(home_claude, rest)
        return (config.SCOPE_GLOBAL, dest) if dest is not None else None
    if prefix == config.ARCHIVE_PROJECTS_PREFIX:
        dest = _safe_join(root, rest)
        return (config.SCOPE_PROJECTS, dest) if dest is not None else None
    return None


def _scope_allows(item_scope: str, requested: str) -> bool:
    if requested == config.SCOPE_ALL:
        return True
    return item_scope == requested


def _plan_from_manifest(
    man: dict[str, Any],
    root: Path,
    home_claude: Path,
    scope: str,
    selection: set[str] | None,
) -> list[PlannedItem]:
    items: list[PlannedItem] = []
    for entry in man.get("entries", []):
        arcname = entry["arcname"]
        mapped = _destination_for(arcname, root, home_claude)
        if mapped is None:
            continue  # unsafe or unknown prefix — never restore
        item_scope, dest = mapped
        if not _scope_allows(item_scope, scope) or (
            selection is not None and arcname not in selection
        ):
            items.append(PlannedItem(arcname, item_scope, dest, Action.SKIP))
            continue
        action = Action.OVERWRITE if dest.exists() else Action.CREATE
        items.append(PlannedItem(arcname, item_scope, dest, action))
    return items


def plan(
    zip_path: Path,
    password: str,
    root: Path,
    scope: str = config.SCOPE_ALL,
    home_claude: Path | None = None,
    selection: Iterable[str] | None = None,
) -> list[PlannedItem]:
    """Compute the restore actions without modifying anything."""
    if scope not in config.VALID_SCOPES:
        raise ValueError(f"Invalid scope {scope!r}; expected one of {config.VALID_SCOPES}")

    root = Path(root).resolve()
    home_claude = (home_claude or config.global_claude_dir()).resolve()
    man = archive.read_manifest(Path(zip_path), password)
    sel = set(selection) if selection is not None else None
    return _plan_from_manifest(man, root, home_claude, scope, sel)


def run_import(
    zip_path: Path,
    password: str,
    root: Path,
    scope: str = config.SCOPE_ALL,
    home_claude: Path | None = None,
    dry_run: bool = False,
    backup_root: Path | None = None,
    selection: Iterable[str] | None = None,
) -> ImportResult:
    """Restore *zip_path* onto disk (or preview it when *dry_run* is true)."""
    root = Path(root).resolve()
    home_claude = (home_claude or config.global_claude_dir()).resolve()
    sel = set(selection) if selection is not None else None

    man = archive.read_manifest(Path(zip_path), password)
    items = _plan_from_manifest(man, root, home_claude, scope, sel)

    if dry_run:
        return ImportResult(dry_run=True, scope=scope, items=items, backup_dir=None)

    sha_map = {e["arcname"]: e.get("sha256") for e in man.get("entries", [])}
    # Created lazily on the first overwrite, so a failed or backup-free import
    # never leaves an empty timestamped directory behind (empty dirs would eat
    # retention slots in `prune_backups` and clutter the backup listing).
    backup_dir: Path | None = None

    # Extract once to a temp directory, then move files to their destinations.
    with tempfile.TemporaryDirectory(prefix="claude-code-sync-import-") as tmp:
        tmp_dir = archive.extract_all(Path(zip_path), Path(tmp), password)
        actionable: list[tuple[PlannedItem, Path]] = []
        for item in items:
            if item.action is Action.SKIP:
                continue
            src = tmp_dir / Path(item.arcname)
            if not src.is_file():
                raise IntegrityError(
                    f"{item.arcname!r} is listed in the manifest but missing from "
                    "the archive. Nothing was restored."
                )
            actionable.append((item, src))
        # Verify every checksum before writing anything, so a corrupted archive
        # cannot leave the machine in a half-restored state.
        for item, src in actionable:
            expected = sha_map.get(item.arcname)
            if expected and manifest.sha256_file(src) != expected:
                raise IntegrityError(
                    f"Checksum mismatch for {item.arcname!r}; the archive is likely "
                    "corrupted. Nothing was restored."
                )
        for item, src in actionable:
            # The plan was computed before extraction; re-check the destination
            # at write time so a file created or deleted in the meantime is
            # still backed up (or does not abort the restore midway).
            if item.destination.exists():
                item.action = Action.OVERWRITE
                if backup_dir is None:
                    backup_dir = _make_backup_dir(backup_root)
                _backup_existing(item.destination, backup_dir)
            else:
                item.action = Action.CREATE
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, item.destination)

    return ImportResult(dry_run=False, scope=scope, items=items, backup_dir=backup_dir)


def _make_backup_dir(backup_root: Path | None) -> Path:
    root = Path(backup_root or config.backup_root())
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Second-resolution stamps can collide across rapid imports; suffix rather
    # than share, so one import cannot clobber another's backed-up files.
    candidate = root / stamp
    suffix = 1
    while True:
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            candidate = root / f"{stamp}-{suffix}"
            suffix += 1


def _backup_existing(destination: Path, backup_dir: Path) -> None:
    """Copy an existing destination file into the backup dir, mirroring layout.

    On Windows the drive letter becomes the first path component (``C/...``), so
    identical paths on different drives cannot collide inside the backup.
    """
    anchor = destination.anchor
    relative = destination.as_posix()[len(anchor):] if anchor else destination.as_posix()
    drive = destination.drive
    # Only plain drive letters get a prefix; UNC "drives" contain separators.
    prefix = drive[0] if len(drive) == 2 and drive[1] == ":" else ""
    target = backup_dir / prefix / relative if prefix else backup_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(destination, target)
