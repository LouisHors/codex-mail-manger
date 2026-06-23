from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RUNTIME_CONFIG = {
    "imap_host": "imap.exmail.qq.com",
    "imap_port": 993,
    "keychain_service": "ugreenmailimap",
    "keychain_account": "hors.liu@ugreen.com",
    "obsidian_output_dir": "/Users/ugreen/Library/Mobile Documents/com~apple~CloudDocs/Documents/Obsidian/SquirrelStock/UgreenMail",
    "daily_schedule": "09:30",
}


def ensure_runtime_layout(root: Path) -> None:
    for name in ["config", "state", "logs", "payloads", "output", "templates"]:
        (root / name).mkdir(parents=True, exist_ok=True)


def load_runtime_config(config_path: Path) -> dict:
    if config_path.exists():
        return json.loads(config_path.read_text())
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(DEFAULT_RUNTIME_CONFIG, indent=2, ensure_ascii=False) + "\n")
    return DEFAULT_RUNTIME_CONFIG.copy()


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {
            "last_success_at": None,
            "last_processed_uids": [],
            "current_note_path": None,
            "last_run_summary": None,
        }
    return json.loads(state_path.read_text())


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@contextmanager
def acquire_lock(lock_path: Path, stale_after_seconds: int = 3600):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        stale = time.time() - lock_path.stat().st_mtime > stale_after_seconds
        existing = json.loads(lock_path.read_text())
        if not stale and _is_process_running(existing.get("pid", -1)):
            raise RuntimeError(f"run lock already held: {lock_path}")
        lock_path.unlink()

    payload = {
        "pid": os.getpid(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    lock_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    try:
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()
