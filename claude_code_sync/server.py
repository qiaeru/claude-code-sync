"""Local HTTP server: serves the static web UI and a small JSON API.

The server binds to ``127.0.0.1`` only, so it is never reachable from the
network. It is built entirely on the standard library (``http.server``); no web
framework is required.
"""

from __future__ import annotations

import contextlib
import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import api

#: Host names accepted in the Host/Origin headers (local only). Blocks DNS
#: rebinding and cross-site requests from other origins. Compared against
#: urlparse().hostname, which lowercases and strips IPv6 brackets.
_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

WEBUI_DIR = Path(__file__).resolve().parent / "webui"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
}

_API_ROUTES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "/api/scan": api.handle_scan,
    "/api/export": api.handle_export,
    "/api/import": api.handle_import,
    "/api/pick": api.handle_pick,
    "/api/backups/prune": api.handle_prune_backups,
}

#: Maximum accepted JSON body, to avoid unbounded memory use (16 MiB).
_MAX_BODY = 16 * 1024 * 1024

#: Maximum accepted upload (drag-and-dropped archive) size (256 MiB).
_MAX_UPLOAD = 256 * 1024 * 1024


class _Handler(BaseHTTPRequestHandler):
    server_version = "claude-code-sync"

    # Silence the default noisy per-request logging.
    def log_message(self, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        # GETs leak local info (paths, hostname, backup names), so they get the
        # same Host/Origin validation as POSTs to block DNS rebinding.
        if not self._origin_ok():
            self._send_json(403, {"error": "Forbidden (cross-origin request blocked)."})
            return

        if self.path in ("/", ""):
            self._serve_file(WEBUI_DIR / "index.html")
        elif self.path == "/api/defaults":
            self._send_json(200, api.get_defaults())
        elif self.path == "/api/backups":
            self._send_json(200, api.handle_list_backups())
        elif self.path.startswith("/api/"):
            self._send_json(404, {"error": "Unknown endpoint"})
        else:
            self._serve_static(self.path.lstrip("/"))

    def do_POST(self) -> None:
        if not self._origin_ok():
            self._drain_body()
            self._send_json(403, {"error": "Forbidden (cross-origin request blocked)."})
            return

        if self.path == "/api/quit":
            self._drain_body()
            self._send_json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if self.path == "/api/upload":
            self._handle_upload()
            return

        handler = _API_ROUTES.get(self.path)
        if handler is None:
            self._drain_body()
            self._send_json(404, {"error": "Unknown endpoint"})
            return

        try:
            body = self._read_json_body()
            result = handler(body)
        except api.ApiError as exc:
            self._send_json(exc.status, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})
        else:
            self._send_json(200, result)

    # -- helpers ---------------------------------------------------------

    def _content_length(self) -> int:
        """Parse Content-Length defensively; a malformed header reads as 0."""
        try:
            return int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return 0

    def _drain_body(self) -> None:
        """Consume any request body so the connection is not reset (Windows)."""
        length = self._content_length()
        if length > 0:
            with contextlib.suppress(OSError):
                self.rfile.read(length)

    def _origin_ok(self) -> bool:
        """Reject cross-site requests and DNS-rebinding (Host/Origin must be local)."""
        # urlparse raises ValueError on malformed bracketed IPv6 — reject those too.
        try:
            host = urlparse(f"//{self.headers.get('Host') or ''}").hostname or ""
        except ValueError:
            return False
        if host not in _ALLOWED_HOSTS:
            return False
        origin = self.headers.get("Origin")
        if origin:
            try:
                hostname = urlparse(origin).hostname or ""
            except ValueError:
                return False
            if hostname not in _ALLOWED_HOSTS:
                return False
        return True

    def _handle_upload(self) -> None:
        length = self._content_length()
        if length <= 0:
            self._send_json(400, {"error": "Empty upload."})
            return
        if length > _MAX_UPLOAD:
            self._send_json(413, {"error": "Uploaded file too large."})
            return
        filename = self.headers.get("X-Filename", "dropped.zip")
        try:
            data = self.rfile.read(length)
            result = api.handle_upload(data, filename)
        except api.ApiError as exc:
            self._send_json(exc.status, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})
        else:
            self._send_json(200, result)

    def _read_json_body(self) -> dict[str, Any]:
        length = self._content_length()
        if length <= 0:
            return {}
        if length > _MAX_BODY:
            raise api.ApiError("Request body too large.", status=413)
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise api.ApiError("Invalid JSON body.") from exc
        if not isinstance(data, dict):
            raise api.ApiError("Request body must be a JSON object.")
        return data

    def _serve_static(self, rel: str) -> None:
        # Resolve safely under WEBUI_DIR to prevent path traversal.
        target = (WEBUI_DIR / rel).resolve()
        try:
            target.relative_to(WEBUI_DIR.resolve())
        except ValueError:
            self._send_json(403, {"error": "Forbidden"})
            return
        if target.is_file():
            self._serve_file(target)
        else:
            self._send_json(404, {"error": "Not found"})

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json(404, {"error": "Not found"})
            return
        data = path.read_bytes()
        ctype = _CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        # API responses describe local paths and backups; keep them out of caches.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Create (but do not start) the local server. ``port=0`` picks a free port."""
    return ThreadingHTTPServer((host, port), _Handler)


def serve_forever(server: ThreadingHTTPServer) -> None:
    """Block serving requests until :meth:`shutdown` is called (e.g. via /api/quit)."""
    try:
        server.serve_forever()
    finally:
        server.server_close()
