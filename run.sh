#!/usr/bin/env bash
# Launch Claude Code Sync: start the local server and open the web UI.
set -euo pipefail

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    python=python3
elif command -v python >/dev/null 2>&1; then
    python=python
else
    echo "Python 3.11+ is required, but neither python3 nor python is on your PATH." >&2
    exit 1
fi

# exec so Ctrl-C reaches Python directly and no extra shell lingers while it runs.
exec "$python" -m claude_code_sync "$@"
