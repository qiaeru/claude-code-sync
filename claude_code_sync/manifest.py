"""Build and read the ``manifest.json`` stored inside each archive.

The manifest records what the archive contains and on which machine it was
created, so an import can present an accurate preview and restore files to the
right place.
"""

from __future__ import annotations

import hashlib
import json
import platform
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import config


def sha256_file(path: Path) -> str | None:
    """Return the hex SHA-256 of *path*, or ``None`` if it cannot be read."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def build(manifest_entries: list[dict[str, Any]], scope: str) -> dict[str, Any]:
    """Build the manifest dict around already-computed *manifest_entries*.

    Each entry dict carries ``arcname``/``scope``/``size``/``sha256``, computed
    by :func:`archive._write_entry` from the bytes actually written to the ZIP.
    """
    return {
        "format_version": config.ARCHIVE_VERSION,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "scope": scope,
        "entry_count": len(manifest_entries),
        "entries": manifest_entries,
    }


def dumps(manifest: dict[str, Any]) -> bytes:
    """Serialize a manifest to pretty UTF-8 JSON bytes."""
    return json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")


def loads(data: bytes) -> dict[str, Any]:
    """Parse manifest JSON bytes, validating the format version."""
    manifest = json.loads(data.decode("utf-8"))
    version = manifest.get("format_version")
    if version != config.ARCHIVE_VERSION:
        raise ValueError(
            f"Unsupported archive format version {version!r}; "
            f"this tool understands version {config.ARCHIVE_VERSION}."
        )
    return manifest
