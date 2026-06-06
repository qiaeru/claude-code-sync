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

case "$keep" in
  ''|*[!0-9]*) echo "keep must be a non-negative integer (got: $keep)." >&2; exit 1;;
esac

if [ -z "${CLAUDE_CODE_SYNC_PASSWORD:-}" ]; then
  echo "Set CLAUDE_CODE_SYNC_PASSWORD before running (the export password)." >&2
  exit 1
fi

mkdir -p -- "$out_dir"

# Prefer the installed CLI; fall back to running the package from the repo.
if command -v claude-code-sync >/dev/null 2>&1; then
  claude-code-sync export --root "$root" --scope all --out-dir "$out_dir"
elif command -v python3 >/dev/null 2>&1; then
  ( cd "$repo_dir" && python3 -m claude_code_sync export --root "$root" --scope all --out-dir "$out_dir" )
elif command -v python >/dev/null 2>&1; then
  ( cd "$repo_dir" && python -m claude_code_sync export --root "$root" --scope all --out-dir "$out_dir" )
else
  echo "Neither the claude-code-sync CLI nor Python is available." >&2
  exit 1
fi

# Prune old archives, keeping the newest `keep` by modification time. Sorting by
# mtime (not by name) is robust even if the hostname embedded in the names changes.
shopt -s nullglob
archives=("$out_dir"/claude-code-sync-*.zip)
total=${#archives[@]}
to_delete=$(( total > keep ? total - keep : 0 ))
if [ "$to_delete" -gt 0 ]; then
  readarray -t sorted < <(
    for a in "${archives[@]}"; do
      printf '%s\t%s\n' "$(stat -c %Y -- "$a" 2>/dev/null || stat -f %m -- "$a")" "$a"
    done | sort -rn | cut -f2-
  )
  for (( i = keep; i < total; i++ )); do
    rm -f -- "${sorted[$i]}"
  done
fi

echo "Archive written to $out_dir; kept newest $keep (removed $to_delete)."
