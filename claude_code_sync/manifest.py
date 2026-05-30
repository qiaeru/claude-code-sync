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
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import config
from .scanner import Entry


@dataclass(frozen=True)
class ManifestEntry:
    """One file recorded in the manifest."""

    arcname: str
    scope: str
    size: int
    sha256: str | None = None


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


def build(entries: Iterable[Entry], scope: str) -> dict[str, Any]:
    """Build the manifest dict for *entries* exported under *scope*."""
    manifest_entries: list[dict[str, Any]] = []
    for entry in entries:
        try:
            size = entry.source.stat().st_size
        except OSError:
            size = 0
        manifest_entries.append(
            {
                "arcname": entry.arcname,
                "scope": entry.scope,
                "size": size,
                "sha256": sha256_file(entry.source),
            }
        )

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


def entries(manifest: dict[str, Any]) -> list[ManifestEntry]:
    """Return the manifest entries as typed objects."""
    return [
        ManifestEntry(
            arcname=e["arcname"],
            scope=e["scope"],
            size=int(e.get("size", 0)),
            sha256=e.get("sha256"),
        )
        for e in manifest.get("entries", [])
    ]
