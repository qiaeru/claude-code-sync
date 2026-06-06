#!/usr/bin/env bash
# Prunes the import backups that claude-code-sync writes to
# ~/.claude-code-sync-backups/<timestamp>/, keeping the most recent ones.
# Usage: clean-backups.sh [keep]   (keep defaults to 10). See the README.
#
# The tool never removes these itself, so they accumulate; this is the housekeeping
# it deliberately leaves to you. The script lists what it will delete and asks first.

set -u
shopt -s nullglob

backup_root="$HOME/.claude-code-sync-backups"
keep=${1:-10}

case "$keep" in
  ''|*[!0-9]*) echo "keep must be a non-negative integer (got: $keep)." >&2; exit 1;;
esac

if [ ! -d "$backup_root" ]; then
  echo "No backups found ($backup_root does not exist)."
  exit 0
fi

# Pathname expansion sorts ascending, and the names are timestamps, so the array
# is oldest-first and the tail is the newest `keep` to retain.
dirs=("$backup_root"/*/)
total=${#dirs[@]}
to_delete=$(( total > keep ? total - keep : 0 ))

if [ "$total" -eq 0 ]; then
  echo "No backups found in $backup_root."
  exit 0
fi

if [ "$to_delete" -eq 0 ]; then
  echo "$total backup(s) present, keeping $keep. Nothing to prune."
  exit 0
fi

echo "$total backup(s) present. These $to_delete oldest will be removed:"
for (( i = 0; i < to_delete; i++ )); do
  echo "  $(basename -- "${dirs[$i]%/}")"
done
echo

read -r -p "Delete them? [y/N] " reply
case "$reply" in
  [yY]|[yY][eE][sS]) ;;
  *) echo "Aborted. Nothing deleted."; exit 0;;
esac

for (( i = 0; i < to_delete; i++ )); do
  rm -rf -- "${dirs[$i]}"
done
echo "Removed $to_delete backup(s)."
