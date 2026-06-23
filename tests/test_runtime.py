import json
import os
import time
from pathlib import Path

from runtime import acquire_lock, ensure_runtime_layout, load_state, save_state


def test_ensure_runtime_layout_creates_required_directories(tmp_path: Path) -> None:
    ensure_runtime_layout(tmp_path)

    assert (tmp_path / "config").exists()
    assert (tmp_path / "state").exists()
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "payloads").exists()
    assert (tmp_path / "output").exists()


def test_load_state_defaults_when_file_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "state" / "last_success.json")

    assert state["last_success_at"] is None
    assert state["last_processed_uids"] == []


def test_save_state_writes_json(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "last_success.json"
    save_state(state_path, {"last_success_at": "2026-06-23T01:00:00+00:00"})

    assert json.loads(state_path.read_text())["last_success_at"] == "2026-06-23T01:00:00+00:00"


def test_acquire_lock_replaces_stale_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "state" / "run.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(json.dumps({"pid": 999999, "created_at": "2026-06-23T01:00:00+00:00"}))
    stale_time = time.time() - 7200
    os.utime(lock_path, (stale_time, stale_time))

    with acquire_lock(lock_path, stale_after_seconds=60):
        assert lock_path.exists()
        lock_data = json.loads(lock_path.read_text())
        assert lock_data["pid"] == os.getpid()

    assert not lock_path.exists()
