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

## Summarization backend (pi)

The daily summary is produced by the `pi` agent in non-interactive mode. The prompt is piped on
stdin and the Markdown summary is read from stdout:

```bash
pi -p --no-tools --no-session --no-context-files < prompt.md
```

`pi` can exit 0 even when the backend fails (for example HTTP 429 rate limiting) and then prints the
error payload on stdout. The runner therefore validates that stdout starts with a Markdown heading
and contains all required sections; otherwise the run fails without touching the Obsidian note and
without advancing the checkpoint.

Optional `config/runtime.json` keys:

- `pi_executable` - absolute path to `pi` (defaults to `pi` resolved via `PATH`)
- `pi_model` - `provider/model` override (defaults to the pi default model)
- `pi_timeout_seconds` - per-run timeout (default `900`)

## Agent executable not found

`launchd` starts jobs with a minimal `PATH`. Both `scripts/run_mailautomation.sh` and
`scripts/backfill_mailautomation.sh` export `/Users/ugreen/bin:/opt/homebrew/bin:/usr/local/bin`
before running, and the plist sets `EnvironmentVariables.PATH`. If a `No such file or directory`
error returns, check `which pi` first.
