"""Tests for the framework-free API handlers."""

from __future__ import annotations

import pytest

from claude_code_sync import api


def test_upload_saves_zip_and_returns_path() -> None:
    result = api.handle_upload(b"PK\x03\x04 fake zip", "my archive.zip")
    assert result["name"].endswith(".zip")
    assert result["size"] == len(b"PK\x03\x04 fake zip")
    from pathlib import Path

    saved = Path(result["path"])
    assert saved.is_file()
    assert saved.read_bytes() == b"PK\x03\x04 fake zip"


def test_upload_forces_zip_extension() -> None:
    result = api.handle_upload(b"data", "noext")
    assert result["name"].endswith(".zip")


def test_upload_decodes_percent_encoded_filename() -> None:
    # The web UI sends the name through encodeURIComponent in the X-Filename header.
    result = api.handle_upload(b"data", "mon%20archive%20%C3%A9t%C3%A9.zip")
    assert result["name"] == "mon archive été.zip"


def test_pick_rejects_invalid_kind() -> None:
    with pytest.raises(api.ApiError):
        api.handle_pick({"kind": "banana"})


def test_scan_rejects_missing_root() -> None:
    with pytest.raises(api.ApiError):
        api.handle_scan({"root": "/no/such/dir/hopefully", "scope": "projects"})
