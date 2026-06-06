# backup-export

Create an encrypted claude-code-sync archive with no prompt and prune old ones, for scheduled backups (cron or Task Scheduler).

It wraps `claude-code-sync export`, reading the password from the `CLAUDE_CODE_SYNC_PASSWORD` environment variable so nothing secret reaches the command line. It writes a timestamped archive to a target folder, then keeps only the newest few.

- `backup-export.sh` for Linux, macOS, and Git Bash
- `backup-export.bat` for Windows (cmd or PowerShell)

## Usage

Set the password in the environment, then run it. The output folder defaults to `~/claude-code-sync-archives` and the retention count to 10:

```bash
export CLAUDE_CODE_SYNC_PASSWORD='your-archive-password'
bash scripts/backup-export/backup-export.sh                # default folder, keep 10
./scripts/backup-export/backup-export.sh ~/backups 20      # custom folder, keep 20
```

It exports the same root claude-code-sync syncs (the folder that holds this checkout) with scope `all`.

## Scheduling

On Linux/macOS, run it from cron with the password sourced from a file readable only by you:

```bash
0 9 * * *  CLAUDE_CODE_SYNC_PASSWORD="$(cat ~/.config/ccs-pass)" /path/to/backup-export.sh
```

On Windows, point a Task Scheduler action at `backup-export.bat`, with `CLAUDE_CODE_SYNC_PASSWORD` set for the task.

## Notes

- It reads the password from the environment only, never from an argument.
- It prefers the installed `claude-code-sync` CLI and falls back to `python -m claude_code_sync` from the repo.
- Pruning keeps the newest archives by modification time, so it stays correct even if the hostname in the file names changes.
