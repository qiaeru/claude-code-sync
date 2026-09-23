"""Restore an encrypted archive onto the current machine.

Destinations are derived from each archive member's prefix:

* ``global/<rel>``      -> ``~/.claude/<rel>``
* ``projects/<rel>``    -> ``<root>/<rel>``

Before any existing file is overwritten it is moved into a timestamped backup
directory (``~/.claude-code-sync-backups/<timestamp>/`` by default), preserving
its relative layout. A dry run reports the planned actions without touching disk.

Security: archive member names are validated before use. Any entry that tries to
escape its destination root (``..`` segments, absolute paths, drive letters) is
rejected, so a malicious archive cannot write outside the chosen folders. A
destination that resolves outside its root through a symlink is skipped but kept
visible in the plan, with a reason. Restored files are also checked against the
SHA-256 recorded in the manifest.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from . import archive, config


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
    reason: str | None = None  # why the item is skipped, when it is


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


def _join_parts(base: Path, parts: list[str]) -> Path | None:
    """Join *parts* under *base* syntactically, or ``None`` if a part is malformed.

    Rejects empty/``.``/``..`` segments, embedded separators, and any component
    that looks absolute or carries a drive/anchor.
    """
    for part in parts:
        if not part or part in (".", "..") or "/" in part or "\\" in part:
            return None
        p = Path(part)
        if p.is_absolute() or p.drive or p.anchor:
            return None
    return base.joinpath(*parts)


def _resolves_inside(candidate: Path, base: Path) -> bool:
    """True if *candidate* still lies under *base* once symlinks are resolved."""
    try:
        candidate.resolve().relative_to(base.resolve())
    except (ValueError, OSError):
        return False
    return True


def _destination_for(
    arcname: str, root: Path, home_claude: Path
) -> tuple[str, Path, str | None] | None:
    """Map an *arcname* to ``(scope, destination, skip_reason)``, or ``None``.

    ``None`` means the entry has no meaningful destination to even show (unknown
    prefix, or a malformed/hostile arcname). A non-``None`` *skip_reason* keeps
    the entry visible in the plan while barring it from being restored: silently
    dropping e.g. a symlinked destination would make a dry run look complete
    while the restore quietly misses files.
    """
    parts = arcname.split("/")
    if len(parts) < 2:
        return None
    prefix, rest = parts[0], parts[1:]
    if prefix == config.ARCHIVE_GLOBAL_PREFIX:
        scope, base = config.SCOPE_GLOBAL, home_claude
    elif prefix == config.ARCHIVE_PROJECTS_PREFIX:
        scope, base = config.SCOPE_PROJECTS, root
    else:
        return None
    dest = _join_parts(base, rest)
    if dest is None:
        return None
    if not _resolves_inside(dest, base):
        return (scope, dest, "destination resolves outside its target folder (symlink)")
    return (scope, dest, None)


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
            continue  # hostile or unknown arcname; nothing meaningful to show
        item_scope, dest, unsafe = mapped
        if unsafe:
            items.append(PlannedItem(arcname, item_scope, dest, Action.SKIP, reason=unsafe))
        elif not _scope_allows(item_scope, scope):
            items.append(
                PlannedItem(
                    arcname, item_scope, dest, Action.SKIP, reason="outside the requested scope"
                )
            )
        elif selection is not None and arcname not in selection:
            items.append(PlannedItem(arcname, item_scope, dest, Action.SKIP, reason="not selected"))
        else:
            base = root if item_scope == config.SCOPE_PROJECTS else home_claude
            blocked = _blocked_reason(dest, base)
            if blocked:
                items.append(PlannedItem(arcname, item_scope, dest, Action.SKIP, reason=blocked))
            else:
                action = Action.OVERWRITE if dest.exists() else Action.CREATE
                items.append(PlannedItem(arcname, item_scope, dest, action))
    return items


def _blocked_reason(dest: Path, base: Path) -> str | None:
    """Why *dest* cannot be written as a file, or ``None`` if it can.

    Checked while planning so the conflict shows up in the preview; found only
    at write time, it would abort the restore after earlier files were written.
    """
    if dest.is_dir():
        return "destination is an existing folder"
    for parent in dest.parents:
        if parent == base:
            break
        if parent.exists() and not parent.is_dir():
            return f"{parent.name!r} is an existing file, not a folder"
    return None


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
    # Only the members this restore will actually write are extracted, so a
    # partial import (scope or selection) does not decompress the whole archive.
    needed = {i.arcname for i in items if i.action is not Action.SKIP}
    with tempfile.TemporaryDirectory(prefix="claude-code-sync-import-") as tmp:
        tmp_dir = archive.extract_all(Path(zip_path), Path(tmp), password, members=needed)
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
        # cannot leave the machine in a half-restored state. An entry without a
        # recorded checksum is rejected too: every exporter writes one, so its
        # absence means the manifest was tampered with or hand-crafted.
        for item, src in actionable:
            expected = sha_map.get(item.arcname)
            if not expected:
                raise IntegrityError(
                    f"No checksum recorded for {item.arcname!r}; refusing to restore "
                    "an unverifiable archive. Nothing was restored."
                )
            if _sha256(src) != expected:
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


def _sha256(path: Path) -> str:
    # Hash the extracted file itself, not the stream it came from: two members
    # whose names differ only by case share one temp file on a case-insensitive
    # filesystem, and only reading back what will be copied catches that.
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
