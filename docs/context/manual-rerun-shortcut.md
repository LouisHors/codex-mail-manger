# Manual Rerun Shortcut

## Goal

Provide a one-click manual rerun for afternoon checks without duplicating workflow logic.

## Behavior

- The shortcut should run `/Users/ugreen/hors/mailautomation/scripts/run_mailautomation.sh`
- Pass `--dry-run` only when explicitly creating a preview/debug shortcut
- Do not implement separate mail logic inside the Shortcut

## Expected result

- The same `src/main.py` entry point runs
- Logs append to `logs/YYYY-MM-DD.log`
- Notification behavior stays consistent with scheduled runs
