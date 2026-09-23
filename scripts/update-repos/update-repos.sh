#!/usr/bin/env bash
# Fast-forwards every Git repo in the folder that holds this claude-code-sync
# checkout (or in the folder given as the first argument). See the README to run it.
#
# Why --ff-only: a repo with unpushed or diverged commits is reported and left
# untouched instead of silently merged. The hosting checkout is skipped too, so
# the script never git-pulls the file it is reading itself.

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

echo "Updating repos in $root"
echo

ok=0
attention=0

for d in "$root"/*/; do
  # .git is a file, not a directory, in worktrees and submodules.
  [ -e "$d/.git" ] || continue
  repo=$(cd -- "$d" && pwd)
  [ "$repo" = "$self_repo" ] && continue
  name=$(basename -- "$repo")
  echo "=== $name ==="
  if git -C "$d" pull --ff-only; then
    ok=$((ok + 1))
  else
    echo "!! $name left untouched (fast-forward not possible)"
    attention=$((attention + 1))
  fi
done

echo
echo "Done. $ok ok, $attention need attention."

# Non-zero exit when a repo needs attention, so the script is usable in automation.
exit $(( attention > 0 ))
