"""Create and read AES-256 encrypted ZIP archives via :mod:`pyzipper`.

The archive is a standard WinZip-AES ZIP, so it can also be opened by 7-Zip or
any AES-capable ZIP tool with the same password. The password is only ever held
in memory and passed straight to :mod:`pyzipper`.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pyzipper

from . import config, manifest
from .scanner import Entry


class BadPassword(Exception):
    """Raised when extraction fails because the password is wrong."""


class ArchiveTooLarge(Exception):
    """Raised when an archive decompresses past the allowed size budget."""


#: Default cap on the total decompressed size accepted during an import. Claude
#: Code configuration is tiny, so 1 GiB is generous while still bounding a
#: decompression bomb. Enforced against bytes actually written, not the (forgeable)
#: sizes declared in the ZIP central directory.
MAX_EXTRACT_BYTES = 1 * 1024 * 1024 * 1024

#: Chunk size for streamed reads during extraction.
_EXTRACT_CHUNK = 65536


def create(entries: Iterable[Entry], out_path: Path, password: str, scope: str) -> Path:
    """Write *entries* into an encrypted ZIP at *out_path*.

    A ``manifest.json`` is added at the archive root describing the contents.
    Returns the path to the created archive.
    """
    entries = list(entries)
    if not password:
        raise ValueError("A non-empty password is required to create an archive.")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    man = manifest.build(entries, scope)

    with pyzipper.AESZipFile(
        out_path,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(password.encode("utf-8"))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        zf.writestr(config.ARCHIVE_MANIFEST, manifest.dumps(man))
        for entry in entries:
            zf.write(entry.source, arcname=entry.arcname)

    return out_path


def prune_archives(directory: Path, keep: int) -> list[Path]:
    """Keep the newest *keep* archives in *directory*, delete the older ones.

    "Newest" is by modification time rather than name, so retention stays correct
    even if the hostname embedded in the file names varies. Only files matching
    :data:`config.ARCHIVE_GLOB` are considered. Returns the paths removed.
    """
    if keep < 0:
        raise ValueError("keep must be >= 0")
    directory = Path(directory)
    archives = sorted(
        (p for p in directory.glob(config.ARCHIVE_GLOB) if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed: list[Path] = []
    for path in archives[keep:]:
        try:
            path.unlink()
        except OSError:
            continue
        removed.append(path)
    return removed


def read_manifest(zip_path: Path, password: str) -> dict[str, Any]:
    """Read and return the manifest from an encrypted archive.

    Raises :class:`BadPassword` if the password is incorrect, and
    :class:`FileNotFoundError` if the manifest is missing.
    """
    with _open_for_read(zip_path, password) as zf:
        try:
            data = zf.read(config.ARCHIVE_MANIFEST)
        except KeyError as exc:
            raise FileNotFoundError(
                f"{config.ARCHIVE_MANIFEST} not found in {zip_path}"
            ) from exc
        except RuntimeError as exc:  # pyzipper raises RuntimeError on bad password
            raise BadPassword("Incorrect password for archive.") from exc
        return manifest.loads(data)


def extract_all(
    zip_path: Path,
    dest_dir: Path,
    password: str,
    max_total_bytes: int = MAX_EXTRACT_BYTES,
) -> Path:
    """Extract every archive member into *dest_dir*.

    Members are streamed out one chunk at a time so the *actual* number of
    decompressed bytes is counted; if it exceeds *max_total_bytes* the extraction
    is aborted with :class:`ArchiveTooLarge`. This bounds a decompression bomb
    even when the ZIP central directory understates a member's size.

    Member names that would escape *dest_dir* (``..``, absolute paths, drive
    letters) are skipped rather than written. Returns *dest_dir*. Raises
    :class:`BadPassword` on a wrong password.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    resolved_root = dest_dir.resolve()
    total = 0
    with _open_for_read(zip_path, password) as zf:
        try:
            for info in zf.infolist():
                target = _safe_extract_path(dest_dir, resolved_root, info.filename)
                if target is None:
                    continue  # unsafe member name — never write outside dest_dir
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    while chunk := src.read(_EXTRACT_CHUNK):
                        total += len(chunk)
                        if total > max_total_bytes:
                            raise ArchiveTooLarge(
                                f"Archive decompresses to more than {max_total_bytes} bytes; "
                                "refusing to extract (possible decompression bomb)."
                            )
                        dst.write(chunk)
        except RuntimeError as exc:  # pyzipper raises RuntimeError on bad password
            raise BadPassword("Incorrect password for archive.") from exc
    return dest_dir


def _safe_extract_path(dest_root: Path, resolved_root: Path, name: str) -> Path | None:
    """Resolve a ZIP member *name* under *dest_root*, or ``None`` if it escapes.

    ZIP entries use forward slashes; backslashes are treated as separators too so
    a Windows-style name cannot smuggle a path component past the checks.
    """
    rel = name.replace("\\", "/").rstrip("/")
    if not rel:
        return None
    parts = rel.split("/")
    for part in parts:
        if not part or part in (".", ".."):
            return None
        p = Path(part)
        if p.is_absolute() or p.drive or p.anchor:
            return None
    candidate = dest_root.joinpath(*parts)
    try:
        candidate.resolve().relative_to(resolved_root)
    except (ValueError, OSError):
        return None
    return candidate


def _open_for_read(zip_path: Path, password: str) -> pyzipper.AESZipFile:
    zf = pyzipper.AESZipFile(Path(zip_path), "r")
    zf.setpassword(password.encode("utf-8"))
    return zf
