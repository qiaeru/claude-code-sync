"""JSON request handlers shared by the local web server.

Each handler takes a parsed request body (``dict``) and returns a JSON-safe
``dict``. They are deliberately free of HTTP details so they can be unit-tested
directly. Client errors raise :class:`ApiError`.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import archive, backups, config, importer, scanner

#: Per-process temp directory holding archives uploaded via drag-and-drop.
_UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="claude-code-sync-uploads-"))


class ApiError(Exception):
    """A client-side error carrying an HTTP status code."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _require(body: dict[str, Any], key: str) -> Any:
    if key not in body or body[key] in (None, ""):
        raise ApiError(f"Missing required field: {key!r}")
    return body[key]


def _scope(body: dict[str, Any]) -> str:
    scope = body.get("scope", config.SCOPE_ALL)
    if scope not in config.VALID_SCOPES:
        raise ApiError(f"Invalid scope {scope!r}; expected one of {config.VALID_SCOPES}")
    return scope


def get_defaults() -> dict[str, Any]:
    """Values used to pre-fill the UI form fields."""
    root = config.default_root()
    return {
        "root": str(root),
        "home_claude": str(config.global_claude_dir()),
        "default_out_dir": str(root),
        "scopes": list(config.VALID_SCOPES),
        "tool_dir": config.tool_dir_name(),
        "hostname": socket.gethostname(),
    }


def handle_scan(body: dict[str, Any]) -> dict[str, Any]:
    """Preview the files that would be exported for a root + scope."""
    root = Path(_require(body, "root"))
    scope = _scope(body)
    if not root.is_dir():
        raise ApiError(f"Root directory does not exist: {root}")

    entries = scanner.scan(root, scope)
    # Stat each file once and reuse the size for both the per-entry rows and the
    # total, instead of stat()-ing every file twice.
    sizes = [_safe_size(e.source) for e in entries]
    return {
        "count": len(entries),
        "total_size": sum(sizes),
        "entries": [
            {
                "arcname": e.arcname,
                "scope": e.scope,
                "size": size,
            }
            for e, size in zip(entries, sizes, strict=True)
        ],
    }


def handle_export(body: dict[str, Any]) -> dict[str, Any]:
    """Create an encrypted archive for the given root + scope."""
    root = Path(_require(body, "root"))
    password = _require(body, "password")
    scope = _scope(body)
    if not root.is_dir():
        raise ApiError(f"Root directory does not exist: {root}")

    entries = scanner.scan(root, scope)

    selection = body.get("selection")
    if selection:
        wanted = set(selection)
        entries = [e for e in entries if e.arcname in wanted]

    if not entries:
        raise ApiError("Nothing to export: no Claude Code configuration found.", status=422)

    out_path = _resolve_out_path(body, root)
    archive.create(entries, out_path, password, scope)
    result: dict[str, Any] = {
        "archive": str(out_path),
        "count": len(entries),
        "total_size": scanner.total_size(entries),
    }

    # Optional retention: keep only the newest N archives in the output folder.
    # Only applied for keep >= 1, so the archive just written is always retained.
    keep = _optional_keep(body.get("keep"))
    if keep is not None and keep >= 1:
        result["pruned"] = len(archive.prune_archives(out_path.parent, keep))
    return result


def handle_import(body: dict[str, Any]) -> dict[str, Any]:
    """Restore (or preview) an archive onto this machine."""
    zip_path = Path(_require(body, "archive"))
    password = _require(body, "password")
    root = Path(_require(body, "root"))
    scope = _scope(body)
    dry_run = bool(body.get("dry_run", False))
    selection = body.get("selection")

    if not zip_path.is_file():
        raise ApiError(f"Archive not found: {zip_path}")

    try:
        result = importer.run_import(
            zip_path, password, root, scope=scope, dry_run=dry_run, selection=selection
        )
    except archive.BadPassword as exc:
        raise ApiError(str(exc), status=403) from exc
    except archive.ArchiveTooLarge as exc:
        raise ApiError(str(exc), status=413) from exc
    except importer.IntegrityError as exc:
        raise ApiError(str(exc), status=422) from exc

    return {
        "dry_run": result.dry_run,
        "scope": result.scope,
        "created": result.created,
        "overwritten": result.overwritten,
        "skipped": result.skipped,
        "backup_dir": str(result.backup_dir) if result.backup_dir else None,
        "items": [
            {
                "arcname": i.arcname,
                "scope": i.scope,
                "destination": str(i.destination),
                "action": i.action.value,
            }
            for i in result.items
        ],
    }


# Small script run in an isolated subprocess to show a native OS dialog. Running
# Tk in a worker thread of the HTTP server is unreliable across platforms, so we
# spawn a short-lived process instead and read the chosen path from stdout.
_PICKER_SCRIPT = r"""
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    sys.exit(2)
kind = sys.argv[1]
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
if kind == "file":
    path = filedialog.askopenfilename(
        title="Select archive",
        filetypes=[("Zip archives", "*.zip"), ("All files", "*.*")],
    )
else:
    path = filedialog.askdirectory(title="Select folder")
root.destroy()
sys.stdout.write(path or "")
"""


def _pick_in_process(kind: str) -> str | None:
    """Show a native dialog in-process (used in frozen builds where there is no
    separate Python interpreter to spawn)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise ApiError(
            "Native file dialog unavailable (tkinter not installed). "
            "Please type the path instead.",
            status=501,
        ) from exc
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    if kind == "file":
        path = filedialog.askopenfilename(
            title="Select archive",
            filetypes=[("Zip archives", "*.zip"), ("All files", "*.*")],
        )
    else:
        path = filedialog.askdirectory(title="Select folder")
    root.destroy()
    return path or None


def handle_pick(body: dict[str, Any]) -> dict[str, Any]:
    """Open a native file/folder dialog on the local machine.

    ``kind`` is ``"file"`` or ``"folder"``. Returns ``{"path": <str|None>}``
    (``None`` when the user cancels). Falls back with a clear error if no GUI
    toolkit (tkinter) is available, so the user can still type the path.
    """
    kind = body.get("kind", "file")
    if kind not in ("file", "folder"):
        raise ApiError("Invalid pick kind; expected 'file' or 'folder'.")

    # In a PyInstaller binary there is no standalone interpreter to spawn, so the
    # dialog must run in-process.
    if getattr(sys, "frozen", False):
        return {"path": _pick_in_process(kind)}

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _PICKER_SCRIPT, kind],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ApiError(f"Could not open file dialog: {exc}", status=500) from exc

    if proc.returncode == 2:
        raise ApiError(
            "Native file dialog unavailable (tkinter not installed). "
            "Please type the path instead.",
            status=501,
        )
    if proc.returncode != 0:
        raise ApiError("File dialog failed.", status=500)

    path = proc.stdout.strip()
    return {"path": path or None}


def handle_list_backups() -> dict[str, Any]:
    """List the import backups under ``~/.claude-code-sync-backups``."""
    infos = backups.list_backups()
    return {
        "root": str(config.backup_root()),
        "count": len(infos),
        "total_size": sum(b.size for b in infos),
        "backups": [
            {"name": b.name, "size": b.size, "files": b.files, "mtime": b.mtime}
            for b in infos
        ],
    }


def handle_prune_backups(body: dict[str, Any]) -> dict[str, Any]:
    """Keep the newest ``keep`` backups and remove the rest (or preview a dry run)."""
    keep = _require_keep(body.get("keep"))
    dry_run = bool(body.get("dry_run", False))
    result = backups.prune_backups(keep, dry_run=dry_run)
    return {
        "dry_run": result.dry_run,
        "removed": len(result.removed),
        "kept": len(result.kept),
        "freed": result.freed,
        "removed_names": [b.name for b in result.removed],
    }


def handle_upload(data: bytes, filename: str) -> dict[str, Any]:
    """Save an uploaded archive (drag-and-drop) to a temp file; return its path."""
    name = Path(filename or "dropped.zip").name
    if not name.lower().endswith(".zip"):
        name += ".zip"
    target = _UPLOAD_DIR / name
    target.write_bytes(data)
    return {"path": str(target), "name": name, "size": len(data)}


def _resolve_out_path(body: dict[str, Any], root: Path) -> Path:
    explicit = body.get("out_path")
    if explicit:
        return Path(explicit)

    out_dir = Path(body.get("out_dir") or root)
    return out_dir / config.archive_filename()


def _require_keep(raw: Any) -> int:
    """Parse a required, non-negative integer ``keep`` value from a request."""
    if raw is None or raw == "":
        raise ApiError("Missing required field: 'keep'")
    keep = _optional_keep(raw)
    if keep is None or keep < 0:
        raise ApiError("keep must be a non-negative integer.")
    return keep


def _optional_keep(raw: Any) -> int | None:
    """Parse an optional integer ``keep`` value; ``None`` when absent or invalid."""
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ApiError("keep must be an integer.") from None


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
