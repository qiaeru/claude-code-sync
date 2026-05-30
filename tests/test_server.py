"""Integration tests for the local HTTP server and its routes."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.client import HTTPConnection

import pytest

from claude_code_sync import server


@pytest.fixture
def live_server() -> Iterator[str]:
    httpd = server.create_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[0], httpd.server_address[1]
    try:
        yield f"{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def _request(addr: str, method: str, path: str, body=None, headers=None):
    conn = HTTPConnection(addr, timeout=5)
    payload = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(headers or {})
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    parsed = json.loads(data) if data and resp.getheader("Content-Type", "").startswith(
        "application/json"
    ) else data
    return resp.status, parsed


def test_index_and_static_assets(live_server: str) -> None:
    status, _ = _request(live_server, "GET", "/")
    assert status == 200
    status, _ = _request(live_server, "GET", "/style.css")
    assert status == 200


def test_defaults_endpoint(live_server: str) -> None:
    status, data = _request(live_server, "GET", "/api/defaults")
    assert status == 200
    assert "root" in data and "hostname" in data


def test_static_traversal_blocked(live_server: str) -> None:
    status, _ = _request(live_server, "GET", "/../server.py")
    assert status in (403, 404)


def test_unknown_api_returns_404(live_server: str) -> None:
    status, _ = _request(live_server, "POST", "/api/nope", body={})
    assert status == 404


def test_cross_origin_post_blocked(live_server: str) -> None:
    status, data = _request(
        live_server, "POST", "/api/scan",
        body={"root": ".", "scope": "projects"},
        headers={"Origin": "http://evil.example"},
    )
    assert status == 403
    assert "cross-origin" in data["error"].lower()


def test_same_origin_scan_ok(live_server: str, tmp_path) -> None:
    status, data = _request(
        live_server, "POST", "/api/scan",
        body={"root": str(tmp_path), "scope": "projects"},
        headers={"Origin": f"http://{live_server}"},
    )
    assert status == 200
    assert data["count"] == 0


def test_upload_roundtrip(live_server: str) -> None:
    conn = HTTPConnection(live_server, timeout=5)
    conn.request(
        "POST", "/api/upload", body=b"PK\x03\x04 fake",
        headers={"X-Filename": "drop.zip", "Content-Type": "application/octet-stream"},
    )
    resp = conn.getresponse()
    data = json.loads(resp.read())
    conn.close()
    assert resp.status == 200
    assert data["name"] == "drop.zip"
