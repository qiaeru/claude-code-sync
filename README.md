# Claude Code Sync

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/qiaeru/claude-code-sync)](https://github.com/qiaeru/claude-code-sync/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/qiaeru/claude-code-sync?style=social)](https://github.com/qiaeru/claude-code-sync/stargazers)

A small tool that syncs your [Claude Code](https://claude.com/claude-code) configuration across machines, offline and encrypted.

Instead of relying on an online service, it bundles your config into a single password-protected ZIP (AES-256) that you move however you like (USB stick, your own cloud, scp…) and import on another machine. A small local web UI drives both export and import, so you never have to remember command-line flags; a headless CLI is available for automation. Inspired by [jean-claude](https://github.com/MikeVeerman/jean-claude), then rebuilt for an offline, encrypted export/import workflow.

> **Offline by design.** No account, no telemetry, no external network call at runtime. The web UI binds to `127.0.0.1` only, and your password never leaves memory.

## Highlights

### What it does

- **Two scopes.** Per-project config (every `CLAUDE.md` at any depth and the project `.claude/` directory) and the global `~/.claude/` (`settings.json`, `keybindings.json`, `CLAUDE.md`, and the `skills/`, `agents/`, `commands/`, `hooks/`, `plugins/` directories).
- **Encrypted, portable archives.** Standard WinZip-AES (AES-256) ZIPs you can also open with 7-Zip or any AES-capable tool using the same password.
- **Safe imports.** Existing files are backed up to `~/.claude-code-sync-backups/<timestamp>/` before being overwritten, every restored file is verified against a SHA-256 in the manifest, and a dry-run previews the changes first.
- **Selective sync.** Tick or untick individual files in the preview to export or restore only a subset.
- **Web UI and CLI.** A claude.ai-flavoured local UI with light/dark themes, drag-and-drop, and native file pickers, plus `export` / `import` subcommands for scripts and cron.

### Under the hood

- **Your secrets stay put.** The global scope uses a strict allow list, so files like `~/.claude/.credentials.json`, your chat history, and `settings.local.json` are never archived.
- **Hardened.** Path-traversal rejection and size-bounded extraction (decompression-bomb guard) on import, archive integrity checks, a local-only server that rejects cross-origin / DNS-rebinding requests.
- **Self-contained.** One runtime dependency (`pyzipper`); the web server is pure standard library; fonts and icons are bundled. Runs unmodified on an air-gapped host.
- **Quality-gated.** Type-hinted, `ruff`- and `mypy`-clean, tested on Linux and Windows via GitHub Actions.

## Requirements

- Python 3.11+
- One runtime dependency: [`pyzipper`](https://pypi.org/project/pyzipper/) (AES ZIP)

## Quick start

Place the `claude-code-sync` folder directly inside the directory that holds your projects (the folder whose sub-folders are your repos), then:

```bash
git clone https://github.com/qiaeru/claude-code-sync.git
cd claude-code-sync
pip install -r requirements.txt        # or: pip install .

python -m claude_code_sync             # launches the web UI in your browser
# or double-click run.bat (Windows) / run ./run.sh (Linux/macOS)
```

In the **Export** tab, check the root, choose a scope, set a password, preview, then create the archive. Move the resulting `claude-code-sync-<host>-<timestamp>.zip` to the other machine and restore it from the **Import** tab (dry-run first).

For automation, the same logic is available headless (here `~/GitHub` is an example; use the folder that contains your projects):

```bash
claude-code-sync export --root ~/GitHub --scope all --out-dir .
claude-code-sync import bundle.zip --root ~/GitHub --dry-run
```

## Documentation

- [Usage guide](./docs/usage.md): scopes, passwords, backups, troubleshooting.
- [CLI reference](./docs/cli.md): headless `export` / `import`.
- [Configuration](./docs/configuration.md): the optional `.claude-code-sync.toml`.
- [What is collected](./docs/what-is-collected.md): exact include/exclude rules.
- [Architecture](./docs/architecture.md): local server, JSON API, core modules.
- [Security](./docs/security.md): encryption, hardening, threat model.
- [Development](./docs/development.md): setup, tests, project layout.
- [Building a binary](./docs/build.md): standalone executable via PyInstaller.
- [Contributing](./CONTRIBUTING.md)
- [Changelog](./CHANGELOG.md)

## Credits

Third-party assets and libraries and their licences are listed in [CREDITS.md](./CREDITS.md).

## License

Released under the MIT License. See [LICENSE](./LICENSE) for the full text.
