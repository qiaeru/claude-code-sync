# Development

## Setup

Prerequisites: Python 3.11+ and a modern browser.

```bash
git clone https://github.com/qiaeru/claude-code-sync.git
cd claude-code-sync
pip install -e ".[dev]"     # editable install with dev tools
```

## Running

```bash
python -m claude_code_sync              # web UI (opens a browser)
python -m claude_code_sync --no-browser # web UI without opening a browser
python -m claude_code_sync --port 8765  # fixed port
python -m claude_code_sync export --help
python -m claude_code_sync import --help
```

## Quality gates

```bash
ruff check .     # lint + import sorting
mypy             # static type checking
pytest -q        # tests
pytest --cov     # tests with coverage
```

All three run in CI (GitHub Actions) on Linux and Windows across Python 3.11–3.13.

## Project layout

```text
claude_code_sync/
├── config.py      # constants, ScanConfig, .claude-code-sync.toml loading
├── scanner.py     # discover files to export (projects + global); pure
├── archive.py     # AES-256 ZIP create/read via pyzipper
├── manifest.py    # manifest.json build/parse + SHA-256 helper
├── importer.py    # plan + restore, backups, traversal & integrity checks
├── api.py         # framework-free request handlers (dict in, dict out)
├── server.py      # stdlib HTTP server: serves webui/ + routes /api/*
├── __main__.py    # entry point: web UI or headless export/import
└── webui/         # static HTML/CSS/JS, bundled fonts and icons
tests/             # round-trip, security, config, selection, server, CLI
docs/              # user and contributor documentation
```

The core modules (`config`, `scanner`, `archive`, `manifest`, `importer`) are UI-agnostic and unit-tested without starting a server. The web layer (`api`, `server`) is a thin shell over them, and the CLI in `__main__` reuses the same core.

## Conventions

- Modern Python (3.11+): `X | None` unions, builtin generics, `StrEnum`, `tomllib`, `collections.abc`.
- The enforced lint rule set lives in `pyproject.toml` (`[tool.ruff.lint]`).
- Update `CHANGELOG.md` (`[Unreleased]`) and the relevant `docs/*.md` whenever public behaviour changes. See [CONTRIBUTING.md](../CONTRIBUTING.md).
