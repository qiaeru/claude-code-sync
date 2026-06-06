#!/usr/bin/env bash
# Shows the Git status of every repo in the folder that holds this claude-code-sync
# checkout (or in the folder given as the first argument): branch, working-tree
# state, and how far ahead/behind its upstream each one is. Read-only. See the README.
#
# Ahead/behind is measured against the last fetched state, so it stays offline and
# fast; run update-repos (or git fetch) first to refresh it. The hosting checkout
# is skipped, like update-repos.

set -u
shopt -s nullglob

command -v git >/dev/null 2>&1 || { echo "git is not on your PATH." >&2; exit 1; }

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
self_repo=$(cd -- "$script_dir/../.." && pwd)

if [ $# -gt 0 ] && [ ! -d "$1" ]; then
  echo "Folder not found: $1" >&2
  exit 1
fi
root=${1:-$(cd -- "$script_dir/../../.." && pwd)}

echo "Status in $root"
echo

attention=0

for d in "$root"/*/; do
  # .git is a file, not a directory, in worktrees and submodules.
  [ -e "$d/.git" ] || continue
  repo=$(cd -- "$d" && pwd)
  [ "$repo" = "$self_repo" ] && continue
  name=$(basename -- "$repo")

  branch=$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  [ "$branch" = "HEAD" ] && branch="(detached)"

  changes=$(git -C "$d" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [ "$changes" -eq 0 ]; then state="clean"; else state="$changes changed"; fi

  ahead=0; behind=0; sync="no upstream"
  if counts=$(git -C "$d" rev-list --left-right --count '@{upstream}...HEAD' 2>/dev/null); then
    behind=${counts%%[[:space:]]*}
    ahead=${counts##*[[:space:]]}
    if   [ "$ahead" -eq 0 ] && [ "$behind" -eq 0 ]; then sync="up to date"
    elif [ "$behind" -eq 0 ];                       then sync="ahead $ahead"
    elif [ "$ahead" -eq 0 ];                        then sync="behind $behind"
    else                                                 sync="ahead $ahead, behind $behind"
    fi
  fi

  printf '%-22s %-18s %-14s %s\n' "$name" "$branch" "$state" "$sync"

  if [ "$changes" -ne 0 ] || [ "$ahead" -ne 0 ] || [ "$behind" -ne 0 ]; then
    attention=$((attention + 1))
  fi
done

echo
echo "Done. $attention repo(s) need attention."

# Non-zero exit when a repo has local changes or is out of sync, for automation.
exit $(( attention > 0 ))
