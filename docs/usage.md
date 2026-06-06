# Usage guide

## Where to place the tool

Put the `claude-code-sync` folder **directly inside the directory that contains your projects**. For example, if your repositories live in `GitHub/`, the layout becomes:

```text
GitHub/
├── claude-code-sync/   <- this tool
├── project-a/
├── project-b/
└── project-c/
```

By default the tool scans its **parent** folder (`GitHub/`) and treats each sibling directory as a project. It always excludes its own folder from the scan.

## Launching

Any of the following start the local server and open the web UI:

```bash
python -m claude_code_sync    # all platforms
claude-code-sync              # if installed with `pip install .`
run.bat                       # Windows (double-click)
./run.sh                      # Linux/macOS
```

Useful flags:

| Flag | Description |
| --- | --- |
| `--no-browser` | Start the server without opening a browser. |
| `--port N` | Bind to a specific port (default: a free one). |
| `--host H` | Bind host (default `127.0.0.1`; keep it local). |
| `--version` | Print the version and exit. |

## Exporting

1. Open the **Export** tab.
2. **Root folder to scan**: pre-filled with the tool's parent folder; edit it or use **Browse…** to pick another.
3. **Scope**:
   - *Projects + global*: everything (default).
   - *Projects only*: just the scanned project folders.
   - *Global only*: just `~/.claude/`.
4. **Output folder**: where the `.zip` is written.
5. **Keep newest archives** (optional): after the export, delete older `claude-code-sync-*.zip` in the output folder beyond this many (by modification time). Leave it blank to keep all.
6. **Password** + **Confirm password**: required. You will need it to import; it is never stored. A strength meter helps you pick a strong one.
7. Click **Preview files** to see what will be included, then **Create encrypted archive**. The result shows the archive path with a **Copy path** button.

The archive is named `claude-code-sync-<hostname>-<YYYYMMDD-HHMMSS>.zip`.

## Importing

1. Move the archive to the target machine and launch the tool there.
2. Open the **Import** tab.
3. **Archive file**: type the path, click **Browse…**, or **drag & drop** the `.zip` onto the drop zone.
4. **Target root folder**: where `projects/…` entries are restored. Global entries always go to that machine's `~/.claude/`.
5. **Scope**: restore everything, or just projects/global.
6. **Password**: the one used at export time.
7. Click **Dry run (preview)** to see what would change. **Restore archive** asks for confirmation (showing how many files will be created/overwritten) before writing.

### Backups

Before any existing file is overwritten, it is copied into:

```text
~/.claude-code-sync-backups/<YYYYMMDD-HHMMSS>/
```

mirroring its original path. If nothing is overwritten, no backup folder is kept.

## Managing backups

The **Backups** tab lists every backup folder under `~/.claude-code-sync-backups/` with its size and file count, newest first. Set **Keep newest** to the number you want to retain and click **Prune older backups**; a confirmation shows how many will be removed and how much space they free before anything is deleted. Pruning touches only that directory, never your repositories or live config.

## Opening the archive manually

The archive is a standard AES-256 ZIP. You can also open it with 7-Zip, WinRAR, or any AES-capable ZIP tool using the same password, which lets you inspect contents without running an import.

## Troubleshooting

- **"Incorrect password for archive."** The password does not match the one used at export.
- **"Nothing to export…"** No `CLAUDE.md` or `.claude/` was found under the chosen root/scope. Check the root folder.
- **Browser did not open.** Open the URL printed in the terminal, or rerun without `--no-browser`.
- **Port already in use.** Pass a different `--port`, or let the default pick a free one.
- **"Native file dialog unavailable".** The Browse… button needs `tkinter`; install it (e.g. `python3-tk` on Linux) or type/drag the path instead.
