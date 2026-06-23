# Mail Automation Workflow Implementation Plan

> **Execution note:** After this plan is approved, use `horspowers:executing-plans` or `horspowers:subagent-driven-development` to implement it task-by-task in the current host.

**Date**: 2026-06-23

## Goal

Build a local mail automation workflow under `~/hors/mailautomation` that checks incremental IMAP mail, asks Codex to produce a Chinese daily summary, updates one Obsidian note per day, supports scheduled and manual reruns, and reports each run result.

## Architecture

Use a two-stage local workflow. A local Python collector reads the mailbox via IMAP using credentials from macOS Keychain, normalizes only new messages since the last successful run, and stores a run payload plus state under `~/hors/mailautomation`. A Codex-triggered summarization step turns that payload into the final Markdown summary, and a local post-processing step writes or updates the daily Obsidian note, sends a macOS notification, and records run status.

## Stack

- Python 3 standard library (`imaplib`, `email`, `json`, `subprocess`, `pathlib`, `datetime`)
- macOS `security`, `osascript`, `open`
- Codex automation for the summarization step
- Horspowers docs system for planning and progress tracking

---

### Task 1: Bootstrap the local workspace

**Files:**
- Create: `~/hors/mailautomation/.horspowers-config.yaml`
- Create: `~/hors/mailautomation/docs/plans/`
- Create: `~/hors/mailautomation/docs/active/`
- Create: `~/hors/mailautomation/docs/archive/`
- Create: `~/hors/mailautomation/docs/context/`
- Create: `~/hors/mailautomation/docs/.docs-metadata/`
- Create: `~/hors/mailautomation/README.md`
- Create: `~/hors/mailautomation/.gitignore`

**Step 1: Initialize Horspowers config**

Run:
```bash
node -e "import { initializeConfig } from '/Users/ugreen/hors/horspowers/lib/config-manager.js'; console.log(initializeConfig('/Users/ugreen/hors/mailautomation', 'personal').message)"
```

Expected: config file exists with `documentation.enabled: true`.

**Step 2: Initialize docs structure**

Run:
```bash
node -e "const { UnifiedDocsManager } = require('/Users/ugreen/hors/horspowers/lib/docs-core.js'); const manager = new UnifiedDocsManager('/Users/ugreen/hors/mailautomation'); manager.updateIndex(); console.log('docs ready at', manager.docsRoot)"
```

Expected: `docs/plans`, `docs/active`, `docs/archive`, `docs/context`, and `docs/.docs-metadata` exist.

**Step 3: Add repo guidance files**

Create `README.md` with a short operator guide and `.gitignore` covering `state/`, `logs/`, `payloads/`, and generated outputs.

**Step 4: Verify bootstrap**

Run:
```bash
find /Users/ugreen/hors/mailautomation/docs -maxdepth 2 -type d | sort
```

Expected: all Horspowers docs directories are listed.

### Task 2: Define runtime layout and state management

**Files:**
- Create: `~/hors/mailautomation/config/runtime.json`
- Create: `~/hors/mailautomation/state/last_success.json`
- Create: `~/hors/mailautomation/state/run.lock`
- Create: `~/hors/mailautomation/logs/`
- Create: `~/hors/mailautomation/payloads/`
- Create: `~/hors/mailautomation/output/`

**Step 1: Write runtime config**

Add runtime settings for:
- IMAP host `imap.exmail.qq.com`
- IMAP port `993`
- Keychain service `ugreenmailimap`
- Keychain account `hors.liu@ugreen.com`
- Obsidian output directory `/Users/ugreen/Library/Mobile Documents/com~apple~CloudDocs/Documents/Obsidian/SquirrelStock/UgreenMail`
- Daily schedule `09:30`

**Step 2: Define state schema**

Record:
- `last_success_at`
- `last_processed_uids`
- `current_note_path`
- `last_run_summary`

**Step 3: Define lock behavior**

Use a PID/timestamp lock file with stale-lock cleanup so a hung run does not block the next day forever.

**Step 4: Verify state bootstrap**

Run:
```bash
python3 -c "from pathlib import Path; base=Path('/Users/ugreen/hors/mailautomation'); print(all((base/p).exists() for p in ['config','state','logs','payloads','output']))"
```

Expected: prints `True`.

### Task 3: Build the incremental IMAP collector

**Files:**
- Create: `~/hors/mailautomation/src/collector.py`
- Create: `~/hors/mailautomation/src/keychain.py`
- Create: `~/hors/mailautomation/src/mail_parser.py`
- Create: `~/hors/mailautomation/tests/test_mail_parser.py`
- Create: `~/hors/mailautomation/tests/test_state_window.py`

**Step 1: Write failing parser tests**

Cover:
- decoding MIME subjects and names
- extracting plain text from multipart messages
- filtering only messages newer than the last success checkpoint
- retaining message IDs and IMAP UIDs for deduplication

**Step 2: Read credentials from Keychain**

Implement `keychain.py` to call:
```bash
security find-generic-password -a "hors.liu@ugreen.com" -s "ugreenmailimap" -w
```

Return only the password to the collector, never log it.

**Step 3: Implement IMAP fetch**

Collector behavior:
- connect with SSL to `imap.exmail.qq.com:993`
- login using Keychain password
- select `INBOX`
- fetch UIDs and RFC822 content for messages newer than the saved checkpoint
- normalize sender, recipients, subject, sent time, text body, message ID, and UID

**Step 4: Persist a payload**

Write one payload per run to `payloads/YYYY-MM-DDTHH-MM-SS.json` containing only newly found messages and checkpoint metadata.

**Step 5: Verify collector**

Run:
```bash
python3 -m pytest /Users/ugreen/hors/mailautomation/tests/test_mail_parser.py -v
python3 /Users/ugreen/hors/mailautomation/src/collector.py --dry-run
```

Expected: tests pass, dry run prints new message count without writing the final note.

### Task 4: Build the Codex summarization handoff

**Files:**
- Create: `~/hors/mailautomation/src/prompt_builder.py`
- Create: `~/hors/mailautomation/templates/daily_summary_prompt.md`
- Create: `~/hors/mailautomation/src/run_summary.py`
- Create: `~/hors/mailautomation/tests/test_prompt_builder.py`

**Step 1: Define the summary contract**

Prompt requirements:
- Chinese output
- sections: quick overview, needs attention, possible replies, important message details, run metadata
- “aggressive” classification for attention/reply candidates
- return valid Markdown only

**Step 2: Build prompt generation**

Prompt builder should inject:
- run time window
- normalized new messages
- user preferences from this plan
- instructions to update a same-day note instead of creating a new one conceptually

**Step 3: Connect to Codex automation**

Design `run_summary.py` to either:
- emit a self-contained prompt file for Codex automation to consume, or
- invoke the chosen Codex automation hook directly once implemented

For the first implementation, prefer a prompt artifact plus structured JSON manifest so the interface is easy to inspect.

**Step 4: Verify prompt quality**

Run:
```bash
python3 -m pytest /Users/ugreen/hors/mailautomation/tests/test_prompt_builder.py -v
python3 /Users/ugreen/hors/mailautomation/src/run_summary.py --preview
```

Expected: preview prints the generated Markdown prompt scaffold and references the payload path.

### Task 5: Update the daily Obsidian note and notifications

**Files:**
- Create: `~/hors/mailautomation/src/note_writer.py`
- Create: `~/hors/mailautomation/src/notifier.py`
- Create: `~/hors/mailautomation/tests/test_note_writer.py`

**Step 1: Define note layout**

Daily note path:
`/Users/ugreen/Library/Mobile Documents/com~apple~CloudDocs/Documents/Obsidian/SquirrelStock/UgreenMail/YYYY-MM-DD.md`

Layout:
- title with date
- refreshed quick overview at top
- append-only run sections with timestamps
- machine-readable footer block for last processed checkpoint

**Step 2: Implement idempotent update logic**

If the day note exists:
- replace the top overview block
- append a new run section only for newly summarized messages

If no new mail exists:
- do not touch the note
- still record the run status

**Step 3: Implement local notification**

Send a macOS notification summarizing:
- whether new mail was found
- whether the note was updated
- whether attention/reply items exist

Click action should open the daily note through `obsidian://` or a direct `open` fallback.

**Step 4: Verify note updates**

Run:
```bash
python3 -m pytest /Users/ugreen/hors/mailautomation/tests/test_note_writer.py -v
python3 /Users/ugreen/hors/mailautomation/src/note_writer.py --sample
```

Expected: sample run updates a local fixture note predictably.

### Task 6: Orchestrate end-to-end runs

**Files:**
- Create: `~/hors/mailautomation/src/main.py`
- Create: `~/hors/mailautomation/tests/test_orchestration.py`
- Modify: `~/hors/mailautomation/src/collector.py`
- Modify: `~/hors/mailautomation/src/run_summary.py`
- Modify: `~/hors/mailautomation/src/note_writer.py`

**Step 1: Write orchestration tests**

Cover:
- no new mail path
- new mail path
- summarization failure path
- stale lock cleanup
- state update only after a successful full run

**Step 2: Implement main workflow**

Execution order:
1. acquire lock
2. load runtime config and state
3. collect incremental mail
4. short-circuit if zero new mail
5. build summary prompt and obtain summary output
6. update same-day Obsidian note
7. notify user and print run report
8. update state
9. release lock

**Step 3: Standardize run reporting**

Every run should emit a concise report with:
- run start time
- new message count
- updated note path or “unchanged”
- attention/reply counts
- success/failure reason

**Step 4: Verify orchestration**

Run:
```bash
python3 -m pytest /Users/ugreen/hors/mailautomation/tests/test_orchestration.py -v
python3 /Users/ugreen/hors/mailautomation/src/main.py --dry-run
```

Expected: orchestration tests pass and dry run prints a complete run summary.

### Task 7: Add scheduling and manual rerun entry points

**Files:**
- Create: `~/hors/mailautomation/launchd/com.ugreen.mailautomation.plist`
- Create: `~/hors/mailautomation/scripts/run_mailautomation.sh`
- Create: `~/hors/mailautomation/docs/context/manual-rerun-shortcut.md`

**Step 1: Build the scheduled runner**

`run_mailautomation.sh` should:
- set a predictable working directory
- invoke `src/main.py`
- append stdout/stderr to dated logs

**Step 2: Define launchd schedule**

Run daily at `09:30` local time and ensure the job does not keep spawning duplicates.

**Step 3: Define Shortcut behavior**

Keep the shortcut narrow:
- one click executes the same runner script
- no separate business logic
- intended for afternoon reruns

Document the exact shortcut behavior and expected input/output in `docs/context/manual-rerun-shortcut.md`.

**Step 4: Verify triggers**

Run:
```bash
plutil -lint /Users/ugreen/hors/mailautomation/launchd/com.ugreen.mailautomation.plist
bash /Users/ugreen/hors/mailautomation/scripts/run_mailautomation.sh --dry-run
```

Expected: plist is valid and the runner script successfully invokes dry-run mode.

### Task 8: Add operator docs and recovery guidance

**Files:**
- Create: `~/hors/mailautomation/docs/context/operations.md`
- Create: `~/hors/mailautomation/docs/context/failure-recovery.md`
- Modify: `~/hors/mailautomation/README.md`

**Step 1: Document routine operations**

Include:
- how to manually rerun
- how to inspect latest logs
- how to confirm the last checkpoint
- how to rotate the Keychain credential

**Step 2: Document failure recovery**

Include:
- clearing a stale lock
- replaying a payload
- re-running summary generation for the same day
- restoring from a broken state file backup

**Step 3: Final verification**

Run:
```bash
find /Users/ugreen/hors/mailautomation/docs -type f | sort
```

Expected: plan, task, and operator docs are present.
