# clean-backups

Prune the import backups that claude-code-sync leaves in `~/.claude-code-sync-backups/` (`%USERPROFILE%\.claude-code-sync-backups\` on Windows), keeping only the most recent ones.

Every import copies the files it is about to overwrite into a timestamped folder there, and the tool never removes them, so they pile up. The tool leaves this housekeeping to you. The script lists what it will delete and asks before removing anything.

- `clean-backups.sh` for Linux, macOS, and Git Bash
- `clean-backups.bat` for Windows (cmd or PowerShell)

## Usage

The number to keep defaults to 10. Pass a different count as the first argument:

```bash
bash scripts/clean-backups/clean-backups.sh        # keep the 10 newest
./scripts/clean-backups/clean-backups.sh 5         # keep the 5 newest
```

On Windows, double-click `clean-backups.bat` or run it from a terminal.

## Notes

- Backups are named by timestamp, so "newest" is unambiguous.
- It touches only `~/.claude-code-sync-backups/`; it never reads your repos or config.
- Deletion is confirmed interactively before anything is removed.
