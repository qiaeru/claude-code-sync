"""Build and read the ``manifest.json`` stored inside each archive.

The manifest records what the archive contains and on which machine it was
created, so an import can present an accurate preview and restore files to the
right place.
"""

from __future__ import annotations

import json
import platform
import socket
from datetime import UTC, datetime
from typing import Any

from . import config


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


def total_size(manifest: dict[str, Any]) -> int:
    """Total bytes archived, as recorded per entry."""
    return sum(int(e.get("size", 0)) for e in manifest.get("entries", []))


def dumps(manifest: dict[str, Any]) -> bytes:
    """Serialize a manifest to pretty UTF-8 JSON bytes."""
    return json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")


def loads(data: bytes) -> dict[str, Any]:
    """Parse manifest JSON bytes, validating the format version and entry shape."""
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Manifest must be a JSON object.")
    manifest: dict[str, Any] = parsed
    version = manifest.get("format_version")
    if version != config.ARCHIVE_VERSION:
        raise ValueError(
            f"Unsupported archive format version {version!r}; "
            f"this tool understands version {config.ARCHIVE_VERSION}."
        )
    entries = manifest.get("entries", [])
    if not isinstance(entries, list) or not all(
        isinstance(e, dict)
        and isinstance(e.get("arcname"), str)
        and e["arcname"]
        and isinstance(e.get("size", 0), int)
        for e in entries
    ):
        raise ValueError(
            "Malformed manifest: every entry must be an object with an 'arcname' "
            "and an integer 'size'."
        )
    return manifest
