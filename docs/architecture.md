# Architecture

The project separates **UI-agnostic core logic** from a **thin local web layer**, so the core can be tested (and reused by a future CLI) without a server.

```text
[ Browser ]  HTML/CSS/JS  (claude_code_sync/webui/)
     |  fetch() JSON
     v
[ Local HTTP server ]  127.0.0.1 only   (server.py + api.py)
     |  calls core functions
     v
[ Core logic ]  scanner / archive / importer / manifest / config
     |
     v
[ Filesystem ]  projects + ~/.claude/   <->   encrypted .zip
```

## Modules

| Module | Responsibility |
| --- | --- |
| `config.py` | Constants: include/exclude lists, archive layout, default paths, scope names. The global **allow list** lives here. |
| `scanner.py` | Pure discovery. Returns `Entry(source, arcname, scope)` objects for the project and global scopes; never writes. |
| `manifest.py` | Build/parse `manifest.json` (format version, host, OS, scope, entries). |
| `archive.py` | Create and read **AES-256** ZIP archives via `pyzipper`. Raises `BadPassword` on wrong password. |
| `importer.py` | Map archive members to destinations, back up existing files, and restore. Supports dry-run and scope filtering. |
| `api.py` | Framework-free request handlers (`dict` in, `dict` out). Raises `ApiError` with an HTTP status for client errors. |
| `server.py` | Standard-library `ThreadingHTTPServer` bound to `127.0.0.1`; serves `webui/` and routes `/api/*` to `api.py`. |
| `__main__.py` | Entry point: with no subcommand starts the server and opens the browser (`--host`, `--port`, `--no-browser`, `--version`); the `export` / `import` subcommands run the same core headless. |

## HTTP API

All endpoints are local-only. Request and response bodies are JSON, except `/api/upload` which takes the raw archive bytes.

| Method & path | Body | Returns |
| --- | --- | --- |
| `GET /api/defaults` | — | Default root, `~/.claude` path, scopes, hostname. |
| `POST /api/scan` | `{root, scope}` | `{count, total_size, entries[]}` preview. |
| `POST /api/export` | `{root, scope, password, out_dir?, out_path?, selection?}` | `{archive, count, total_size}`. |
| `POST /api/import` | `{archive, root, scope, password, dry_run?, selection?}` | Plan/result with per-file actions and backup dir. |
| `POST /api/pick` | `{kind: "file"\|"folder"}` | `{path}` from a native OS dialog (or `null` if cancelled). |
| `POST /api/upload` | raw bytes + `X-Filename` header | `{path, name, size}` of the saved temp archive (drag-and-drop). |
| `POST /api/quit` | `{}` | Stops the server. |

## Design choices

- **No web framework** — only the Python standard library, plus `pyzipper` for AES ZIP. Easy to audit and to run anywhere Python is available.
- **Local-only binding** (`127.0.0.1`) so the server is never reachable from the network.
- **Allow list for global config** so secrets cannot leak even as Claude Code evolves (see [what-is-collected.md](what-is-collected.md)).
- **Backup before overwrite** so an import is always reversible.
- **Manifest with a `format_version`** so future archive-format changes can be detected and handled.
- **Native dialogs run in a subprocess** so Tk never touches the HTTP server's worker threads.

## Testing

`tests/` builds fake project and `~/.claude` trees (including secrets) and verifies: correct collection, strict secret exclusion, an export→import round-trip, dry-run safety, scope filtering, backup-before-overwrite, and the upload/pick API handlers.
