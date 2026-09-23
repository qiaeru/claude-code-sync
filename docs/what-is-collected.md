# What is collected

The exact rules live in [`claude_code_sync/config.py`](../claude_code_sync/config.py). This page summarizes them. The lists can be extended per-root via [`.claude-code-sync.toml`](configuration.md).

## Project scope

For each **direct sub-folder** of the scanned root (excluding the tool's own folder):

**Included**

- Every `CLAUDE.md`, `CLAUDE.local.md`, and `AGENTS.md`, at the project root and in any sub-directory. Claude Code reads `AGENTS.md` in place of, or alongside, `CLAUDE.md`; `CLAUDE.local.md` holds your personal, usually gitignored instructions, so it is the file most easily lost when changing machines. To keep one of these files out of archives, list its name under `secrets.names` in [`.claude-code-sync.toml`](configuration.md).
- The project's `.claude/` directory, recursively, typically `skills/`, `agents/`, `hooks/`, `commands/`, `rules/`, and `settings.json`.

**Excluded**

- `.claude/settings.local.json` (machine-specific).
- `.claude/.credentials.json` and other known secrets, including any `.env` or `.env.*` file.
- `.claude/worktrees/`: the full git checkouts Claude Code creates for `--worktree` sessions (often with gitignored `.env` files copied in by `.worktreeinclude`), not configuration.
- Noisy directories anywhere in the tree, which are never descended into: `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`, `vendor`, `target`, `.next`, `.cache`, `.idea`, `.tox`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`.

## Global scope (`~/.claude/`)

The global scope uses an **allow list**: only the items below are collected. Anything not on the list (including future additions) is ignored, which keeps secrets out of the archive by design.

**Included**

- Files: `settings.json`, `keybindings.json`, `CLAUDE.md`.
- Directories (recursively): `skills/`, `agents/`, `commands/`, `hooks/`, `rules/`, `output-styles/`, `workflows/`, `agent-memory/`, `themes/`.

**Never included**

- `.credentials.json` (your auth tokens).
- `plugins/` (see [Plugins](#plugins) below).
- `projects/`, `todos/`, `history*`, `statsig/`, `shell-snapshots/`, `logs/`, and any other unlisted file or directory.
- `settings.local.json` (machine-specific).

## Plugins

`~/.claude/plugins/` is not collected. Most of it is re-downloadable cache (marketplace clones and installed plugin copies, often tens of megabytes), its state files (`installed_plugins.json`, `known_marketplaces.json`) record this machine's absolute paths, and `plugins/data/` is where plugins keep their own data. Restored on another machine, those state files leave plugins failing to load until they are reinstalled.

The portable part travels in `settings.json`: `enabledPlugins` lists your plugins and `extraKnownMarketplaces` your marketplaces. On the new machine, Claude Code recognizes the marketplaces declared there; add them and install the plugins with `/plugin` or `claude plugin marketplace add` / `claude plugin install`.

To archive the whole directory anyway (both machines share the same home path), add `plugins` to `include_dirs` in [`.claude-code-sync.toml`](configuration.md).

## Why an allow list for the global scope?

Using an allow list (rather than a deny list) means that if Claude Code starts writing a new sensitive file into `~/.claude/`, it will **not** be picked up unless we explicitly add it here. This is a deliberate safety choice: the worst case is that a new config file is missed, never that a secret leaks.

## Archive layout

```text
claude-code-sync-<host>-<timestamp>.zip   (AES-256 encrypted)
├── manifest.json     # format version, date, host, OS, scope, entry list
├── global/           # mirror of the included parts of ~/.claude/
└── projects/
    └── <project>/...
```

On import, `global/…` is restored to `~/.claude/…` and `projects/<p>/…` to `<target-root>/<p>/…`. Each entry carries a SHA-256 in `manifest.json` that is verified on import, and entries are validated so a crafted archive cannot write outside the target folders.

## Symlinks

By default the scanner does **not** follow symlinks: symlinked **directories** are not descended into (this avoids loops and surprises), and symlinked **files** found while walking a tree are **skipped** rather than archived, so an export can never pull in content from outside the scanned tree. Set `scan.follow_symlinks = true` in [`.claude-code-sync.toml`](configuration.md) to traverse symlinked directories and archive symlinked files.

> One exception: the allow-listed global top-level files (`~/.claude/settings.json`, `keybindings.json`, `CLAUDE.md`) are always collected even when they are symlinks, since symlinking these is the normal dotfile-manager setup.
