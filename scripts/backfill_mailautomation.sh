#!/bin/bash
set -euo pipefail

# Same PATH hardening as run_mailautomation.sh so the pi agent resolves under launchd.
export PATH="/Users/ugreen/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FROM_DATE=""
TO_DATE=""
DRY_RUN=()

usage() {
  echo "Usage: $0 --from YYYY-MM-DD --to YYYY-MM-DD [--dry-run]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from)
      FROM_DATE="${2:-}"
      shift 2
      ;;
    --to)
      TO_DATE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=(--dry-run)
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$FROM_DATE" || -z "$TO_DATE" ]]; then
  usage
  exit 2
fi

"$ROOT/.venv/bin/python" - "$FROM_DATE" "$TO_DATE" <<'PY' | while read -r note_date until_utc; do
from datetime import date, datetime, time, timedelta, timezone
from sys import argv
from zoneinfo import ZoneInfo

start = date.fromisoformat(argv[1])
end = date.fromisoformat(argv[2])
if start > end:
    raise SystemExit("--from must be on or before --to")

current = start
while current <= end:
    local_until = datetime.combine(current, time(9, 30), tzinfo=ZoneInfo("Asia/Shanghai"))
    print(current.isoformat(), local_until.astimezone(timezone.utc).isoformat())
    current += timedelta(days=1)
PY
  echo "Backfilling $note_date through $until_utc"
  bash "$ROOT/scripts/run_mailautomation.sh" "${DRY_RUN[@]}" --note-date "$note_date" --until "$until_utc"
done
