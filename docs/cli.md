# Command-line interface

Besides the web UI, the tool can run **headless**, which suits scripts, cron jobs, or machines without a browser. The CLI uses the same core logic as the UI.

With no subcommand the tool launches the web UI (see [usage.md](usage.md)). The `export` and `import` subcommands run without a browser.

## Password handling

Passwords are never passed as command-line arguments (they would leak into shell history). Provide the password either:

- interactively, when prompted (hidden input), or
- via the `CLAUDE_CODE_SYNC_PASSWORD` environment variable (useful for automation).

## Export

```bash
claude-code-sync export [--root DIR] [--scope all|projects|global] [--out-dir DIR | --out FILE] [--keep N]
```

- `--root`: folder to scan (default: the tool's parent folder).
- `--scope`: `all` (default), `projects`, or `global`.
- `--out-dir`: folder to write the archive into (default: the root).
- `--out`: exact output path (overrides `--out-dir`).
- `--keep N`: after exporting, keep only the newest `N` `claude-code-sync-*.zip` archives in the output folder (by modification time) and delete the rest. Handy for scheduled backups.

You are prompted for the password twice (to confirm), unless `CLAUDE_CODE_SYNC_PASSWORD` is set.

```bash
# Example: export everything into the current directory.
# Replace ~/GitHub with the folder that contains your projects.
CLAUDE_CODE_SYNC_PASSWORD='correct horse battery staple' \
  claude-code-sync export --root ~/GitHub --scope all --out-dir .
```

## Import

```bash
claude-code-sync import ARCHIVE [--root DIR] [--scope ...] [--dry-run] [--yes]
```

- `ARCHIVE`: path to the `.zip` to restore.
- `--root`: target root for `projects/…` entries (default: auto). Global entries always go to `~/.claude/`.
- `--scope`: restore everything or just projects/global.
- `--dry-run`: print the plan and exit without writing.
- `--yes`: skip the overwrite confirmation prompt.

```bash
# Preview first, then restore non-interactively
claude-code-sync import bundle.zip --root ~/GitHub --dry-run
CLAUDE_CODE_SYNC_PASSWORD=... claude-code-sync import bundle.zip --root ~/GitHub --yes
```

Existing files are backed up to `~/.claude-code-sync-backups/<timestamp>/` before being overwritten, and every file is verified against the SHA-256 recorded in the archive manifest before anything is written.
