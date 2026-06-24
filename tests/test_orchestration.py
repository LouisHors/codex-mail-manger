from pathlib import Path

from main import _notification_target, run_workflow


def test_run_workflow_short_circuits_when_no_new_mail(tmp_path: Path) -> None:
    state_updates = []
    notifications = []
    note_calls = []

    def fake_collect(*_args, **_kwargs):
        return {
            "new_messages": [],
            "unread_count": 7,
            "unread_uids": ["26", "27", "28", "29", "31", "32", "33"],
            "checkpoint": {"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": []},
            "payload_path": None,
        }

    report = run_workflow(
        root=tmp_path,
        dry_run=True,
        collector=fake_collect,
        summarize=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not summarize")),
        write_note=lambda **kwargs: note_calls.append(kwargs) or {"updated": True, "path": str(tmp_path / "note.md")},
        notify=lambda title, message, open_target=None: notifications.append((title, message, open_target)),
        save_state_func=lambda path, state: state_updates.append((path, state)),
    )

    assert report["status"] == "success"
    assert report["new_message_count"] == 0
    assert report["unread_count"] == 7
    assert report["note_path"] == str(tmp_path / "note.md")
    assert state_updates == []
    assert note_calls
    assert note_calls[0]["unread_count"] == 7
    assert notifications
    assert notifications[0][1] == "未读 7 / 新增 0"


def test_run_workflow_updates_note_when_new_mail_exists(tmp_path: Path) -> None:
    summary_calls = []
    note_calls = []
    notifications = []

    def fake_collect(*_args, **_kwargs):
        payload_path = tmp_path / "payloads" / "2026-06-23T09-30-00.json"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text("{}")
        return {
            "new_messages": [{"uid": "1001"}],
            "unread_count": 4,
            "unread_uids": ["1001", "1002", "1003", "1004"],
            "checkpoint": {"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": ["1001"]},
            "payload_path": payload_path,
        }

    def fake_summarize(*, payload_path, runtime_config, dry_run):
        summary_calls.append((payload_path, runtime_config, dry_run))
        return {
            "summary_markdown": "# 快速概览\n有 1 封需要关注的邮件。\n\n# 需要关注\n- A\n- B\n\n# 可能需要回复\n- R1\n- R2\n- R3\n\n# 重要邮件详情\n- C\n\n# 运行元数据\n- D",
            "prompt_path": str(tmp_path / "output" / "prompt.md"),
            "manifest_path": str(tmp_path / "output" / "manifest.json"),
            "summary_path": str(tmp_path / "output" / "summary.md"),
        }

    def fake_write_note(**kwargs):
        note_calls.append(kwargs)
        return {"updated": True, "path": str(tmp_path / "note.md")}

    report = run_workflow(
        root=tmp_path,
        dry_run=False,
        collector=fake_collect,
        summarize=fake_summarize,
        write_note=fake_write_note,
        notify=lambda title, message, open_target=None: notifications.append((title, message, open_target)),
        save_state_func=lambda *_args, **_kwargs: None,
    )

    assert report["status"] == "success"
    assert report["new_message_count"] == 1
    assert report["unread_count"] == 4
    assert report["note_path"] == str(tmp_path / "note.md")
    assert report["attention_count"] == 2
    assert report["reply_count"] == 3
    assert summary_calls
    assert note_calls
    assert notifications
    assert notifications[0][1] == "未读 4 / 新增 1"


def test_run_workflow_reports_failure_without_saving_state(tmp_path: Path) -> None:
    saved_state = []

    def fake_collect(*_args, **_kwargs):
        payload_path = tmp_path / "payloads" / "2026-06-23T09-30-00.json"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text("{}")
        return {
            "new_messages": [{"uid": "1001"}],
            "unread_count": 1,
            "unread_uids": ["1001"],
            "checkpoint": {"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": ["1001"]},
            "payload_path": payload_path,
        }

    report = run_workflow(
        root=tmp_path,
        dry_run=False,
        collector=fake_collect,
        summarize=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("summary failed")),
        write_note=lambda **_kwargs: {"updated": True, "path": str(tmp_path / "note.md")},
        notify=lambda *_args, **_kwargs: None,
        save_state_func=lambda path, state: saved_state.append((path, state)),
    )

    assert report["status"] == "failure"
    assert "summary failed" in report["reason"]
    assert saved_state == []


def test_run_workflow_dry_run_does_not_persist_state(tmp_path: Path) -> None:
    saved_state = []

    def fake_collect(*_args, **_kwargs):
        return {
            "new_messages": [],
            "unread_count": 3,
            "unread_uids": ["2001", "2002", "2003"],
            "checkpoint": {"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": []},
            "payload_path": None,
        }

    report = run_workflow(
        root=tmp_path,
        dry_run=True,
        collector=fake_collect,
        summarize=lambda **_kwargs: {"summary_markdown": ""},
        write_note=lambda **_kwargs: {"updated": False, "path": str(tmp_path / "note.md")},
        notify=lambda *_args, **_kwargs: None,
        save_state_func=lambda path, state: saved_state.append((path, state)),
    )

    assert report["status"] == "success"
    assert saved_state == []


def test_run_workflow_counts_only_top_level_reply_candidates(tmp_path: Path) -> None:
    def fake_collect(*_args, **_kwargs):
        payload_path = tmp_path / "payloads" / "2026-06-23T09-30-00.json"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text("{}")
        return {
            "new_messages": [{"uid": "1001"}],
            "unread_count": 2,
            "unread_uids": ["1001", "1002"],
            "checkpoint": {"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": ["1001"]},
            "payload_path": payload_path,
        }

    def fake_summarize(*, payload_path, runtime_config, dry_run):
        return {
            "summary_markdown": "# 快速概览\n概览。\n\n# 需要关注\n- A\n- B\n\n# 可能需要回复\n- R1\n  - reason\n  - action\n\n# 重要邮件详情\n- C\n\n# 运行元数据\n- D",
            "prompt_path": str(tmp_path / "output" / "prompt.md"),
            "manifest_path": str(tmp_path / "output" / "manifest.json"),
            "summary_path": str(tmp_path / "output" / "summary.md"),
        }

    report = run_workflow(
        root=tmp_path,
        dry_run=False,
        collector=fake_collect,
        summarize=fake_summarize,
        write_note=lambda **_kwargs: {"updated": True, "path": str(tmp_path / "note.md")},
        notify=lambda *_args, **_kwargs: None,
        save_state_func=lambda *_args, **_kwargs: None,
    )

    assert report["attention_count"] == 2
    assert report["reply_count"] == 1


def test_notification_target_uses_file_uri_for_dry_run(tmp_path: Path) -> None:
    note_path = tmp_path / "2026-06-23-dry-run.md"
    expected = note_path.resolve().as_uri()

    assert _notification_target(str(note_path), dry_run=True) == expected


def test_notification_target_uses_obsidian_url_for_real_run(tmp_path: Path) -> None:
    note_path = tmp_path / "2026-06-23.md"

    assert _notification_target(str(note_path), dry_run=False) == (
        f"obsidian://open?path={note_path.resolve().as_posix()}"
    )
