# Contributing to Claude Code Sync

Thank you for considering a contribution. The project is small by design and must stay approachable: a single runtime dependency, a standard-library web server, and no build step for the UI. Changes that keep it simple are the ones most likely to land.

## Ground rules

- **English everywhere in the source tree.** This applies to comments, commit messages, pull request descriptions, documentation, identifiers (variables, functions, API paths) and anything else a reviewer reads, as well as the web UI strings.
- **Offline-first, no runtime network calls.** The tool must keep working on an air-gapped machine. Fonts (Inter, Source Serif 4) are self-hosted and icons (Heroicons) are inlined as SVG; nothing is fetched from a third party at runtime.
- **Keep the dependency surface tiny.** `pyzipper` is the only runtime dependency. TOML parsing uses the standard-library `tomllib`. Please do not add runtime dependencies without a strong reason.
- **No telemetry, no analytics.** Ever. Passwords stay in memory and are never written to disk or passed as command-line arguments.
- **Security first.** Preserve the allow-list for the global scope (secrets such as `~/.claude/.credentials.json` must never be archived), the path-traversal checks on import, and the local-only / origin-checked HTTP server.

## Development setup

Prerequisites:

- Python 3.11 or later.
- A modern browser (for the web UI).

```bash
# Clone
git clone https://github.com/qiaeru/claude-code-sync.git
cd claude-code-sync

# Install the package with its dev tools (editable)
pip install -e ".[dev]"

# Launch the web UI
python -m claude_code_sync

# Quality gates
ruff check .     # lint
mypy             # type-check
pytest -q        # tests
```

The core logic (`scanner`, `archive`, `importer`, `manifest`, `config`) is UI-agnostic and unit-tested without a server; the web layer (`server`, `api`) is a thin shell over it.

## Workflow

Branch from `main`, open a pull request, and let the CI checks (ruff, mypy, pytest on Linux + Windows) pass. Keep commits atomic (one feature, one bug-fix, one refactor) and use Conventional Commit prefixes (`fix:`, `feat:`, `chore:`, `docs:`, `refactor:`), optionally scoped with the touched area (`fix(importer):`, `feat(cli):`). Pull request titles follow the same rule and stay at or below seventy characters.

Before pushing: review every added comment in the diff, update the relevant `docs/*.md` if the change affects public behavior, and tighten the `[Unreleased]` section of `CHANGELOG.md`.

## Code style

- Type-hinted, `ruff`- and `mypy`-clean. The enforced rule set is in `pyproject.toml`.
- Modern Python (3.11+): `X | None` unions, builtin generics, `StrEnum`, `tomllib`, `collections.abc`.
- Core modules never import the web layer, so they stay easy to test and reuse from the CLI.
- The global-scope collection uses an **allow list**, never a deny list, so new config files are missed rather than risking a secret leak.

## Documentation

If the change touches public behavior, the collected file set, the HTTP/JSON API, the archive format, or anything a user or contributor might look up later, update both `CHANGELOG.md` (under `[Unreleased]`) and the relevant page under `docs/` (usage, cli, configuration, what-is-collected, architecture, security, development, build).

## Reporting issues

Open a GitHub issue with a minimal reproduction and the OS plus Python version you observed it on. For security-sensitive reports, open a private security advisory on GitHub instead of a public issue.

## License

By submitting a contribution, you agree that it is released under the MIT license shipped with this repo.
