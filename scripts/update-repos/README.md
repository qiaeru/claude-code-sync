# update-repos

Update **every Git repository** in one run by fast-forwarding each repo's current branch to its latest pushed version.

This pairs with [Claude Code Sync](../../README.md). The sync tool sits in the folder that holds your project repos and treats each sibling as a project. These scripts run from right here inside that checkout and target the same folder, so the sync tool keeps your Claude Code config in step across machines while `update-repos` keeps the repos themselves current on both sides.

Two versions of the same tool:

- `update-repos.sh` for Linux, macOS, and Git Bash
- `update-repos.bat` for Windows (cmd or PowerShell)

## Usage

Run the script in place, no copying or setup. It resolves its own location, walks up to the folder that holds this `claude-code-sync` checkout, and updates every repo it finds there:

```text
my-repos/                          ← the scripts target this folder
├── claude-code-sync/
│   └── scripts/update-repos/
│       ├── update-repos.sh        ← run it from here
│       └── update-repos.bat
├── project-a/                     (a git repo)
├── project-b/                     (a git repo)
└── notes/                         (a git repo)
```

**Linux / Git Bash**:

```bash
bash scripts/update-repos/update-repos.sh
```

Or make it executable once and run it directly:

```bash
chmod +x scripts/update-repos/update-repos.sh
./scripts/update-repos/update-repos.sh
```

**Windows**: double-click `update-repos.bat`, or run it from a terminal.

To update a different folder instead, pass it as the first argument:

```bash
./update-repos.sh ~/other-repos
```

## What it does

For every subfolder that is a Git repository, it runs:

```bash
git pull --ff-only
```

`--ff-only` updates a repo only when it can fast-forward cleanly to the remote. A repo with unpushed commits or a diverged branch stays untouched and gets flagged, then the script moves on to the next one. A one-line summary at the end reports how many repos updated and how many need your attention.

## Notes

- Only the **current branch** of each repo updates, not all branches.
- The `claude-code-sync` checkout that hosts the script is skipped, matched by path rather than name, so it works whatever you cloned the folder as. Update it with a plain `git pull`.
- Folders that are not Git repos are skipped.
- Needs `git` on your `PATH`.
