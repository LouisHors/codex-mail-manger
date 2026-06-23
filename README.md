# Mail Automation

Local mail automation workflow for:

- incrementally collecting new IMAP mail from `INBOX`
- generating a Chinese daily summary with Codex
- updating one Obsidian note per day
- supporting scheduled and manual reruns

## Current status

This repository currently contains the planning docs and the initial project skeleton.

## Planned structure

- `docs/` project plans, task tracking, and operator docs
- `src/` workflow implementation
- `tests/` automated tests
- `scripts/` local runner scripts
- `launchd/` scheduled job definitions

## Notes

- Runtime data such as payloads, logs, state files, and generated output are intentionally ignored by Git.
- Git remote is not configured yet.
