from __future__ import annotations

import imaplib
import json
from datetime import datetime, timezone
from email import message_from_bytes
from pathlib import Path

from keychain import get_keychain_password
from mail_parser import normalize_message
from runtime import ensure_runtime_layout, load_runtime_config, load_state


def filter_new_messages(
    messages: list[dict[str, str]],
    checkpoint: datetime,
    seen_uids: set[str],
) -> list[dict[str, str]]:
    filtered = []
    for message in messages:
        uid = message["uid"]
        if uid in seen_uids:
            continue
        sent_at = datetime.fromisoformat(message["sent_at"])
        if sent_at <= checkpoint:
            continue
        filtered.append(message)
    return filtered


def collect_incremental_mail(root: Path, runtime_config: dict, state: dict, dry_run: bool) -> dict:
    checkpoint_raw = state.get("last_success_at")
    checkpoint = (
        datetime.fromisoformat(checkpoint_raw)
        if checkpoint_raw
        else datetime(1970, 1, 1, tzinfo=timezone.utc)
    )
    seen_uids = set(state.get("last_processed_uids", []))

    if dry_run:
        new_messages = _sample_dry_run_messages()
        payload_path = _write_payload(root / "payloads", checkpoint, new_messages)
    else:
        new_messages = _fetch_mail(runtime_config, checkpoint, seen_uids)
        payload_path = _write_payload(root / "payloads", checkpoint, new_messages)

    current_checkpoint = datetime.now(timezone.utc).isoformat()
    uids = list(seen_uids.union({message["uid"] for message in new_messages}))
    return {
        "new_messages": new_messages,
        "checkpoint": {
            "last_success_at": current_checkpoint,
            "last_processed_uids": uids,
        },
        "payload_path": payload_path,
    }


def _fetch_mail(runtime_config: dict, checkpoint: datetime, seen_uids: set[str]) -> list[dict[str, str]]:
    password = get_keychain_password(
        runtime_config["keychain_account"],
        runtime_config["keychain_service"],
    )
    client = imaplib.IMAP4_SSL(runtime_config["imap_host"], runtime_config["imap_port"])
    try:
        client.login(runtime_config["keychain_account"], password)
        client.select("INBOX")
        status, data = client.uid("search", None, "ALL")
        if status != "OK":
            return []
        messages = []
        for uid in data[0].decode().split():
            if uid in seen_uids:
                continue
            fetch_status, fetch_data = client.uid("fetch", uid, "(RFC822)")
            if fetch_status != "OK":
                continue
            raw_message = fetch_data[0][1]
            message = message_from_bytes(raw_message)
            normalized = normalize_message(message, uid=uid)
            sent_at = datetime.fromisoformat(normalized["sent_at"])
            if sent_at <= checkpoint:
                continue
            messages.append(normalized)
        return messages
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _write_payload(payload_dir: Path, checkpoint: datetime, messages: list[dict[str, str]]) -> Path:
    payload_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    payload_path = payload_dir / f"{stamp}.json"
    payload = {
        "window": {
            "from": checkpoint.isoformat(),
            "to": datetime.now(timezone.utc).isoformat(),
        },
        "messages": messages,
    }
    payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload_path


def _sample_dry_run_messages() -> list[dict[str, str]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "uid": "dry-run-001",
            "message_id": "<dry-run-001@mailautomation.local>",
            "subject": "Dry run sample message",
            "sent_at": now.isoformat(),
            "received_at": now.isoformat(),
            "from": {"name": "Dry Run Sender", "email": "dry-run@example.com"},
            "to": [{"name": "Operator", "email": "operator@example.com"}],
            "cc": [],
            "body": "This is a simulated message used for dry-run workflow verification.",
        }
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()

    ensure_runtime_layout(args.root)
    runtime_config = load_runtime_config(args.root / "config" / "runtime.json")
    state = load_state(args.root / "state" / "last_success.json")
    result = collect_incremental_mail(
        root=args.root,
        runtime_config=runtime_config,
        state=state,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            {
                "new_message_count": len(result["new_messages"]),
                "payload_path": str(result["payload_path"]) if result["payload_path"] else None,
                "checkpoint": result["checkpoint"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
