# Operations

## Manual rerun

```bash
bash /Users/ugreen/hors/mailautomation/scripts/run_mailautomation.sh
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
