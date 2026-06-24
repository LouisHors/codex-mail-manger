from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from collector import collect_incremental_mail
from note_writer import update_daily_note
from notifier import send_notification
from run_summary import summarize_payload
from runtime import acquire_lock, ensure_runtime_layout, load_runtime_config, load_state, save_state


def run_workflow(
    root: Path,
    dry_run: bool,
    collector=collect_incremental_mail,
    summarize=summarize_payload,
    write_note=update_daily_note,
    notify=send_notification,
    save_state_func=save_state,
) -> dict:
    ensure_runtime_layout(root)
    runtime_config = load_runtime_config(root / "config" / "runtime.json")
    state_path = root / "state" / "last_success.json"
    state = load_state(state_path)
    lock_path = root / "state" / "run.lock"
    run_started_at = datetime.now(timezone.utc).isoformat()

    try:
        with acquire_lock(lock_path):
            collection = collector(root=root, runtime_config=runtime_config, state=state, dry_run=dry_run)
            new_messages = collection["new_messages"]
            unread_count = collection["unread_count"]
            checkpoint = collection["checkpoint"]
            note_path = _resolve_note_path(root, runtime_config, dry_run)

            if not new_messages:
                note_result = write_note(
                    note_path=note_path,
                    summary_markdown="",
                    checkpoint=checkpoint,
                    run_timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
                    unread_count=unread_count,
                    new_message_count=0,
                )
                report = {
                    "status": "success",
                    "started_at": run_started_at,
                    "new_message_count": 0,
                    "unread_count": unread_count,
                    "note_path": note_result["path"] if note_result["updated"] else "unchanged",
                    "attention_count": 0,
                    "reply_count": 0,
                    "reason": "no new mail",
                }
                if not dry_run:
                    new_state = {
                        **state,
                        **checkpoint,
                        "current_note_path": str(note_path),
                        "last_run_summary": report,
                    }
                    save_state_func(state_path, new_state)
                notify("Mail Automation", _notification_message(unread_count, 0), _notification_target(note_result["path"], dry_run))
                return report

            payload = {
                "window": {
                    "from": state.get("last_success_at") or run_started_at,
                    "to": checkpoint["last_success_at"],
                },
                "messages": new_messages,
            }
            summary = summarize(
                payload_path=collection["payload_path"],
                runtime_config=runtime_config,
                dry_run=dry_run,
            )
            note_result = write_note(
                note_path=note_path,
                summary_markdown=summary["summary_markdown"],
                checkpoint=checkpoint,
                run_timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
                unread_count=unread_count,
                new_message_count=len(new_messages),
            )
            report = {
                "status": "success",
                "started_at": run_started_at,
                "new_message_count": len(new_messages),
                "unread_count": unread_count,
                "note_path": note_result["path"] if note_result["updated"] else "unchanged",
                "attention_count": _count_section_bullets(summary["summary_markdown"], "需要关注"),
                "reply_count": _count_section_bullets(summary["summary_markdown"], "可能需要回复"),
                "reason": "ok",
            }
            if not dry_run:
                new_state = {
                    **state,
                    **checkpoint,
                    "current_note_path": str(note_path),
                    "last_run_summary": report,
                }
                save_state_func(state_path, new_state)
            notify(
                "Mail Automation",
                _notification_message(unread_count, len(new_messages)),
                _notification_target(note_result["path"], dry_run),
            )
            return report
    except Exception as exc:
        report = {
            "status": "failure",
            "started_at": run_started_at,
            "new_message_count": 0,
            "note_path": "unchanged",
            "attention_count": 0,
            "reply_count": 0,
            "reason": str(exc),
        }
        notify("Mail Automation Failed", str(exc), None)
        return report


def _resolve_note_path(root: Path, runtime_config: dict, dry_run: bool) -> Path:
    if dry_run:
        return root / "output" / f"{datetime.now().strftime('%Y-%m-%d')}-dry-run.md"
    return Path(runtime_config["obsidian_output_dir"]) / f"{datetime.now().strftime('%Y-%m-%d')}.md"


def _notification_target(note_path: str, dry_run: bool) -> str:
    path = Path(note_path).expanduser().resolve()
    if dry_run:
        return path.as_uri()
    return f"obsidian://open?path={quote(str(path))}"


def _notification_message(unread_count: int, new_message_count: int) -> str:
    return f"未读 {unread_count} / 新增 {new_message_count}"


def _count_section_bullets(markdown: str, title: str) -> int:
    lines = markdown.splitlines()
    target = f"# {title}"
    found = False
    count = 0
    for line in lines:
        if line == target:
            found = True
            continue
        if found and line.startswith("# "):
            break
        if found and line.startswith("- "):
            count += 1
    return count


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    result = run_workflow(root=args.root, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
