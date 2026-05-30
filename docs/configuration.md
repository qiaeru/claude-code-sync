# Configuration

The built-in include/exclude lists (see [what-is-collected.md](what-is-collected.md)) work out of the box. You can extend them with an optional `.claude-code-sync.toml` file placed in the **scanned root** (the folder whose sub-folders are your projects).

All settings are **additive**: they extend the defaults. Exclusion and secret lists can only be added to, never shrunk, so the safety guarantees (e.g. never archiving `.credentials.json`) always hold.

## Example

```toml
[scan]
# Extra directory names to prune anywhere in the tree.
prune_dirs = ["coverage_html", "tmp"]
# Follow symlinked directories during the scan (default: false).
follow_symlinks = false

[project]
# Extra entries to skip inside each project's .claude/ directory.
exclude = ["local-notes.md"]

[global]
# Extra top-level files/directories to include from ~/.claude/.
include_files = ["mcp.json"]
include_dirs = ["prompts"]

[secrets]
# Extra file names that must never be exported (in any scope).
names = ["api-token.txt"]
```

## Keys

| Section | Key | Meaning |
| --- | --- | --- |
| `scan` | `prune_dirs` | Directory names never descended into. |
| `scan` | `follow_symlinks` | Whether to follow symlinks — descend into symlinked directories and archive symlinked files (default `false`). |
| `project` | `exclude` | Names skipped inside each project `.claude/`. |
| `global` | `include_files` | Extra top-level files collected from `~/.claude/`. |
| `global` | `include_dirs` | Extra top-level directories collected from `~/.claude/`. |
| `secrets` | `names` | File names never exported, in any scope. |

## Symlinks

By default the scanner does **not** follow symlinks. Symlinked directories are
not descended into (this avoids infinite loops and surprises, e.g. a
`.claude/skills` symlinked to a huge tree), and symlinked *files* met while
walking a tree are skipped rather than archived. Set `scan.follow_symlinks = true`
if you intentionally symlink config and want symlinked directories traversed and
symlinked files archived.

The explicitly allow-listed global top-level files (`~/.claude/settings.json`,
`keybindings.json`, `CLAUDE.md`) are an exception: they are always collected even
when symlinked, since that is the common dotfile-manager layout.
