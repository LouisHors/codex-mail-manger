#!/bin/bash
set -euo pipefail

# launchd starts jobs with a minimal PATH that excludes user and Homebrew bin dirs,
# which is why the agent executable was not found. Keep it discoverable.
export PATH="/Users/ugreen/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
STAMP="$(date '+%Y-%m-%d')"
LOG_FILE="$ROOT/logs/$STAMP.log"

"$ROOT/.venv/bin/python" "$ROOT/src/main.py" "$@" >>"$LOG_FILE" 2>&1
