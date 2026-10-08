# Operations

## Manual rerun

```bash
bash /Users/ugreen/hors/mailautomation/scripts/run_mailautomation.sh
```

## Backfill missed daily summaries

Run the backfill script in chronological order. It uses the same workflow as the scheduled job, writes each run to the requested note date, and advances the checkpoint after each successful day.

```bash
bash /Users/ugreen/hors/mailautomation/scripts/backfill_mailautomation.sh --from 2026-07-04 --to 2026-07-06
```

## Dry run

```bash
bash /Users/ugreen/hors/mailautomation/scripts/run_mailautomation.sh --dry-run
```

## Latest logs

```bash
tail -n 200 /Users/ugreen/hors/mailautomation/logs/$(date '+%Y-%m-%d').log
```

## Last checkpoint

```bash
cat /Users/ugreen/hors/mailautomation/state/last_success.json
```

## Rotate IMAP password in Keychain

Update the `ugreenmailimap` generic password for account `hors.liu@ugreen.com` in macOS Keychain Access, then rerun the workflow.
