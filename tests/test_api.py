"""Tests for the framework-free API handlers."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from claude_code_sync import api


def _upload(data: bytes, filename: str) -> dict:
    return api.handle_upload(io.BytesIO(data), len(data), filename)


def test_upload_saves_zip_and_returns_path() -> None:
    payload = b"PK\x03\x04 fake zip"
    result = _upload(payload, "my archive.zip")
    assert result["name"].endswith(".zip")
    assert result["size"] == len(payload)

    saved = Path(result["path"])
    assert saved.is_file()
    assert saved.read_bytes() == payload


def test_upload_forces_zip_extension() -> None:
    result = _upload(b"data", "noext")
    assert result["name"].endswith(".zip")


def test_upload_decodes_percent_encoded_filename() -> None:
    # The web UI sends the name through encodeURIComponent in the X-Filename header.
    result = _upload(b"data", "mon%20archive%20%C3%A9t%C3%A9.zip")
    assert result["name"] == "mon archive été.zip"


def test_truncated_upload_is_rejected_and_removed() -> None:
    # A client that disconnects mid-body delivers fewer bytes than announced;
    # the partial file must not stay behind for a later import to trip over.
    with pytest.raises(api.ApiError):
        api.handle_upload(io.BytesIO(b"short"), 100, "cut.zip")
    assert not (api._get_upload_dir() / "cut.zip").exists()


def test_import_rejects_non_zip_with_clean_error(tmp_path: Path) -> None:
    # Drag-and-dropping a file that is not a real ZIP must surface as a 4xx
    # ApiError (like the CLI's one-line message), not an unhandled 500.
    bogus = tmp_path / "not-a-zip.zip"
    bogus.write_bytes(b"hello, not a zip")
    with pytest.raises(api.ApiError) as excinfo:
        api.handle_import(
            {"archive": str(bogus), "password": "pw", "root": str(tmp_path)}
        )
    assert excinfo.value.status == 422


def test_pick_rejects_invalid_kind() -> None:
    with pytest.raises(api.ApiError):
        api.handle_pick({"kind": "banana"})


def test_scan_rejects_missing_root() -> None:
    with pytest.raises(api.ApiError):
        api.handle_scan({"root": "/no/such/dir/hopefully", "scope": "projects"})
