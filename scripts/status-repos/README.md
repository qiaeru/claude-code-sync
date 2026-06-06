# status-repos

Show the Git status of **every repository** in one read-only pass: current branch, working-tree changes, and how far ahead or behind its upstream each repo is.

It is the read-only companion to [update-repos](../update-repos/): same layout and self-location, but it only reports and never touches a repo. Run it before syncing two machines to see what still has uncommitted or unpushed work.

- `status-repos.sh` for Linux, macOS, and Git Bash
- `status-repos.bat` for Windows (cmd or PowerShell)

## Usage

Run it in place; it targets the folder that holds this `claude-code-sync` checkout. Pass another folder as the first argument to inspect that one instead.

```bash
bash scripts/status-repos/status-repos.sh
./scripts/status-repos/status-repos.sh ~/other-repos
```

On Windows, double-click `status-repos.bat` or run it from a terminal.

## Output

One line per repo:

```text
repo-a                 main               clean          up to date
repo-b                 feature/login      2 changed      ahead 1
notes                  main               clean          behind 3
project-c              develop            clean          no upstream
```

Ahead/behind is measured against the **last fetched** state, so the check stays offline and fast. Run [update-repos](../update-repos/) or `git fetch` first if you need it refreshed. The exit code is non-zero when any repo has local changes or is out of sync, so the script is usable in automation.

## Notes

- The `claude-code-sync` checkout that hosts the script is skipped.
- Folders that are not Git repos are skipped.
- Needs `git` on your `PATH`.
