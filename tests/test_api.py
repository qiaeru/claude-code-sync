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


def test_export_write_failure_is_clean_error(fake_root: Path, tmp_path: Path) -> None:
    # An unwritable output folder (here: a file where a folder should be) must
    # surface as a one-line ApiError, not an unhandled 500.
    blocker = tmp_path / "blocker"
    blocker.write_text("in the way", encoding="utf-8")
    with pytest.raises(api.ApiError) as excinfo:
        api.handle_export(
            {
                "root": str(fake_root),
                "scope": "projects",
                "password": "pw",
                "out_dir": str(blocker),
            }
        )
    assert "Could not write archive" in str(excinfo.value)


def test_pick_rejects_invalid_kind() -> None:
    with pytest.raises(api.ApiError):
        api.handle_pick({"kind": "banana"})


def test_scan_rejects_missing_root() -> None:
    with pytest.raises(api.ApiError):
        api.handle_scan({"root": "/no/such/dir/hopefully", "scope": "projects"})


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"root": 42, "scope": "all"}, "must be a string"),
        ({"root": ".", "password": ["pw"]}, "must be a string"),
        ({"root": ".", "password": "pw", "selection": "projects/a"}, "selection"),
        ({"root": ".", "password": "pw", "out_dir": 7}, "must be a string"),
        ({"root": ".", "password": "pw", "keep": "many"}, "keep must be an integer"),
    ],
)
def test_export_rejects_mistyped_fields(
    body: dict, message: str, tmp_path: Path, monkeypatch
) -> None:
    """Fields are checked before the scan, so the error does not depend on
    what the root holds, and nothing is written for a bad request."""
    # An empty root and no global scope: a late check would lose to "Nothing
    # to export" on any machine, not only on one without a ~/.claude.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(api.ApiError, match=message) as exc:
        api.handle_export({"scope": "projects", **body})
    assert exc.value.status == 400
    assert list(tmp_path.iterdir()) == []


def test_export_with_bad_keep_writes_no_archive(fake_root: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    with pytest.raises(api.ApiError, match="keep must be an integer"):
        api.handle_export(
            {"root": str(fake_root), "password": "pw", "out_dir": str(out_dir), "keep": "x"}
        )
    assert not out_dir.exists() or not any(out_dir.iterdir())
