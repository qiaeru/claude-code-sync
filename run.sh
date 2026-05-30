#!/usr/bin/env bash
# Launch Claude Code Sync: start the local server and open the web UI.
set -euo pipefail

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    python3 -m claude_code_sync "$@"
else
    python -m claude_code_sync "$@"
fi
