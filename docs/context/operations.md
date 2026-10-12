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

`pi` can exit 0 even when the backend fails. Two observed shapes:

- HTTP 429 rate limiting prints an error payload on stdout.
- A prompt near pi's size limit silently returns empty stdout with no usable stderr.

The runner therefore validates the stdout payload (Markdown heading, all required sections) instead
of trusting the exit code, retries empty output a couple of times, and otherwise fails without
touching the Obsidian note and without advancing the checkpoint.

### Oversized backlogs are split automatically

A failed run does not advance the checkpoint, so a backlog keeps growing until the prompt exceeds
what `pi` accepts. Measured against real backlogged mail: ~2.8MB of prompt succeeds, ~3.0MB returns
empty output (exit 0), and >=12MB fails with `400 {"code":"1261","message":"Prompt 超长"}`.

`run_summary` therefore summarizes in chunks bounded by `PI_MAX_PROMPT_BYTES` (2MB, measured on the
rendered prompt, not compact JSON) and merges the per-section bodies. A single message larger than
a chunk has its body shrunk until it fits. This makes a long-neglected backlog recover on its own.

Optional `config/runtime.json` keys:

- `pi_executable` - absolute path to `pi` (defaults to `pi` resolved via `PATH`)
- `pi_model` - `provider/model` override (defaults to the pi default model)
- `pi_timeout_seconds` - per-run timeout (default `900`)
- `pi_empty_output_retries` - retries for empty output (default `2`)

### Error reporting

`pi` always writes startup noise to stderr (`[tapd-cli-env] ...`, extension warnings), so the runner
skips those lines when reporting the failure reason. Without that filter the notification showed the
harmless tapd banner instead of the real error.

## Agent executable not found

`launchd` starts jobs with a minimal `PATH`. Both `scripts/run_mailautomation.sh` and
`scripts/backfill_mailautomation.sh` export `/Users/ugreen/bin:/opt/homebrew/bin:/usr/local/bin`
before running, and the plist sets `EnvironmentVariables.PATH`. If a `No such file or directory`
error returns, check `which pi` first.
