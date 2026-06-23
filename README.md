# Mail Automation

Local mail automation workflow for:

- incrementally collecting new IMAP mail from `INBOX`
- generating a Chinese daily summary with Codex
- updating one Obsidian note per day
- supporting scheduled and manual reruns

## Structure

- `docs/` project plans, task tracking, and operator docs
- `src/` workflow implementation
- `tests/` automated tests
- `scripts/` local runner scripts
- `launchd/` scheduled job definitions
- `config/runtime.json` local runtime configuration
- `templates/daily_summary_prompt.md` summary contract reference

## Quick start

1. Create the local virtualenv and install test tooling:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip pytest
```

2. Confirm or update `config/runtime.json`.

3. Make sure the Keychain item exists:
   service `ugreenmailimap`, account `hors.liu@ugreen.com`

4. Run a dry run:

```bash
.venv/bin/python src/main.py --dry-run
```

5. Run the test suite:

```bash
.venv/bin/python -m pytest tests -q
```

## Scheduling

- Manual runner: `scripts/run_mailautomation.sh`
- `launchd` plist: `launchd/com.ugreen.mailautomation.plist`

## Notes

- Runtime data such as payloads, logs, state files, and generated output are intentionally ignored by Git.
- Git remote is not configured yet.
