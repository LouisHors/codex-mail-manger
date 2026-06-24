#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
STAMP="$(date '+%Y-%m-%d')"
LOG_FILE="$ROOT/logs/$STAMP.log"

"$ROOT/.venv/bin/python" "$ROOT/src/main.py" "$@" >>"$LOG_FILE" 2>&1
