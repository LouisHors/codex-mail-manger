# Failure Recovery

## Clear a stale lock

```bash
rm -f /Users/ugreen/hors/mailautomation/state/run.lock
```

Only do this after confirming no active workflow process is still running.

## Replay a payload

Use an existing payload JSON under `payloads/` as the source of truth and rerun the summarization stage manually from Python if collector access is temporarily unavailable.

## Re-run summary generation for the same day

Reinvoke `src/main.py` after restoring the desired payload or temporarily adjusting `state/last_success.json`.

## Restore a broken state file backup

If `state/last_success.json` is corrupted, replace it with a known-good backup or reconstruct the file with:

```json
{
  "last_success_at": null,
  "last_processed_uids": [],
  "current_note_path": null,
  "last_run_summary": null
}
```
