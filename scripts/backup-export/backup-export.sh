#!/usr/bin/env bash
# Creates an encrypted claude-code-sync archive without prompts and prunes old ones,
# for scheduled backups (cron). Usage: backup-export.sh [out-dir] [keep]
# (out-dir defaults to ~/claude-code-sync-archives, keep to 10). See the README.
#
# The password must come from the CLAUDE_CODE_SYNC_PASSWORD env var, never the
# command line, so it stays out of shell history and process listings.

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "$script_dir/../.." && pwd)
root=$(cd -- "$script_dir/../../.." && pwd)

out_dir=${1:-$HOME/claude-code-sync-archives}
keep=${2:-10}

# At least 1: the archive just written is always among the kept ones.
case "$keep" in
  ''|*[!0-9]*|0*) echo "keep must be a positive integer (got: $keep)." >&2; exit 1;;
esac

if [ -z "${CLAUDE_CODE_SYNC_PASSWORD:-}" ]; then
  echo "Set CLAUDE_CODE_SYNC_PASSWORD before running (the export password)." >&2
  exit 1
fi

mkdir -p -- "$out_dir"
# Absolute, since the Python fallback runs from the repo folder.
out_dir=$(cd -- "$out_dir" && pwd)

# Prefer the installed CLI; fall back to running the package from the repo.
args=(export --root "$root" --scope all --out-dir "$out_dir" --keep "$keep")
if command -v claude-code-sync >/dev/null 2>&1; then
  claude-code-sync "${args[@]}"
elif command -v python3 >/dev/null 2>&1; then
  ( cd "$repo_dir" && python3 -m claude_code_sync "${args[@]}" )
elif command -v python >/dev/null 2>&1; then
  ( cd "$repo_dir" && python -m claude_code_sync "${args[@]}" )
else
  echo "Neither the claude-code-sync CLI nor Python is available." >&2
  exit 1
fi
