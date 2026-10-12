import json
from pathlib import Path

import pytest

import run_summary
from run_summary import run_summary_cli, summarize_payload

def _write_payload(payload_path: Path) -> None:
    payload_path.parent.mkdir(parents=True)
    payload_path.write_text(
        json.dumps(
            {
                "window": {"from": "2026-06-23T00:00:00+00:00", "to": "2026-06-23T01:00:00+00:00"},
                "messages": [{"uid": "1", "subject": "Hello", "from": {"name": "A", "email": "a@example.com"}, "sent_at": "2026-06-23T00:30:00+00:00", "body": "Body"}],
            },
            ensure_ascii=False,
        )
    )


VALID_SUMMARY = "# 快速概览\n真实摘要\n\n# 需要关注\n- A\n\n# 可能需要回复\n- B\n\n# 重要邮件详情\n- C\n\n# 运行元数据\n- D"


def test_summarize_payload_non_dry_run_invokes_pi(tmp_path: Path, monkeypatch) -> None:
    payload_path = tmp_path / "payloads" / "sample.json"
    _write_payload(payload_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class Result:
            returncode = 0
            stderr = ""
            stdout = VALID_SUMMARY

        return Result()

    monkeypatch.setattr("run_summary.subprocess.run", fake_run)
    result = summarize_payload(
        payload_path=payload_path,
        runtime_config={"obsidian_output_dir": str(tmp_path / "notes")},
        dry_run=False,
    )

    assert calls
    cmd, kwargs = calls[0]
    assert Path(cmd[0]).name == "pi"
    assert "-p" in cmd
    assert "--output-last-message" not in cmd
    assert kwargs["input"] == (tmp_path / "output").glob("*-daily-summary-prompt.md").__next__().read_text()
    assert result["summary_markdown"].startswith("# 快速概览")
    assert Path(result["summary_path"]).read_text() == VALID_SUMMARY + "\n"


def test_summarize_payload_rejects_non_markdown_output(tmp_path: Path, monkeypatch) -> None:
    """pi exits 0 even when rate limited, so the raw error text must not be written as a note."""
    payload_path = tmp_path / "payloads" / "sample.json"
    _write_payload(payload_path)

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = '429: {"message":"All available accounts are currently rate-limited."}'

        return Result()

    monkeypatch.setattr("run_summary.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="pi"):
        summarize_payload(
            payload_path=payload_path,
            runtime_config={"obsidian_output_dir": str(tmp_path / "notes")},
            dry_run=False,
        )


def test_summarize_payload_rejects_empty_output(tmp_path: Path, monkeypatch) -> None:
    payload_path = tmp_path / "payloads" / "sample.json"
    _write_payload(payload_path)

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = "   \n"

        return Result()

    monkeypatch.setattr("run_summary.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="empty"):
        summarize_payload(
            payload_path=payload_path,
            runtime_config={"obsidian_output_dir": str(tmp_path / "notes")},
            dry_run=False,
        )


def test_run_summary_cli_uses_real_mode_when_preview_is_false(tmp_path: Path, monkeypatch) -> None:
    payload_path = tmp_path / "payloads" / "sample.json"
    payload_path.parent.mkdir(parents=True)
    payload_path.write_text(
        json.dumps(
            {
                "window": {"from": "2026-06-23T00:00:00+00:00", "to": "2026-06-23T01:00:00+00:00"},
                "messages": [{"uid": "1", "subject": "Hello", "from": {"name": "A", "email": "a@example.com"}, "sent_at": "2026-06-23T00:30:00+00:00", "body": "Body"}],
            },
            ensure_ascii=False,
        )
    )
    recorded = []

    monkeypatch.setattr(
        "run_summary.summarize_payload",
        lambda payload_path, runtime_config, dry_run: recorded.append(dry_run) or {
            "summary_markdown": "# 快速概览\n真实摘要",
            "prompt_path": str(tmp_path / "output" / "prompt.md"),
            "manifest_path": str(tmp_path / "output" / "manifest.json"),
            "summary_path": str(tmp_path / "output" / "summary.md"),
        },
    )

    result = run_summary_cli(root=tmp_path, preview=False, payload_path=payload_path)
    assert recorded == [False]
    assert result["summary_markdown"] == "# 快速概览\n真实摘要"

def test_overlong_prompt_is_chunked_into_multiple_pi_calls(tmp_path: Path, monkeypatch) -> None:
    """A backlogged payload can grow past the pi prompt limit, so it must be split."""
    payload_path = tmp_path / "payloads" / "sample.json"
    payload_path.parent.mkdir(parents=True)
    payload = {
        "window": {"from": "2026-07-28T01:00:00+00:00", "to": "2026-10-12T01:00:00+00:00"},
        "messages": [
            {
                "uid": str(index),
                "subject": f"Subject {index}",
                "from": {"name": "A", "email": "a@example.com"},
                "sent_at": "2026-10-01T00:30:00+00:00",
                "body": "内容" * 200_000,
            }
            for index in range(80)
        ],
    }
    payload_path.write_text(json.dumps(payload, ensure_ascii=False))

    prompts = []

    def fake_run(cmd, **kwargs):
        prompts.append(kwargs["input"])

        class Result:
            returncode = 0
            stderr = ""
            stdout = VALID_SUMMARY

        return Result()

    monkeypatch.setattr("run_summary.subprocess.run", fake_run)
    result = summarize_payload(
        payload_path=payload_path,
        runtime_config={"obsidian_output_dir": str(tmp_path / "notes")},
        dry_run=False,
    )

    assert len(prompts) > 1, "expected the payload to be split into several pi calls"
    assert all(len(prompt.encode()) <= run_summary.PI_MAX_PROMPT_BYTES for prompt in prompts)
    assert result["summary_markdown"].lstrip().startswith("#")
    assert result["summary_markdown"].endswith("\n")


def test_every_prompt_chunk_stays_within_the_pi_limit(tmp_path: Path) -> None:
    payload = {
        "window": {"from": "a", "to": "b"},
        "messages": [
            {"uid": str(index), "subject": "S" * 200, "from": {"name": "A", "email": "a@example.com"},
             "sent_at": "2026-10-01T00:30:00+00:00", "body": "正文" * 200_000}
            for index in range(40)
        ],
    }

    chunks = run_summary._chunk_messages(payload["messages"], payload, "/tmp/note.md")

    assert len(chunks) > 1
    assert sum(len(chunk) for chunk in chunks) == len(payload["messages"])
    for chunk in chunks:
        assert run_summary._prompt_bytes_for(chunk, payload, "/tmp/note.md") <= run_summary.PI_MAX_PROMPT_BYTES

def test_oversized_single_message_is_truncated_to_fit(tmp_path: Path) -> None:
    huge = {
        "uid": "1",
        "subject": "Huge",
        "from": {"name": "A", "email": "a@example.com"},
        "sent_at": "2026-10-01T00:30:00+00:00",
        "body": "字" * 5_000_000,
    }

    payload = {"window": {"from": "a", "to": "b"}}

    chunks = run_summary._chunk_messages([huge], payload, "/tmp/note.md")

    assert len(chunks) == 1
    assert len(chunks[0]) == 1
    assert chunks[0][0]["body"] != huge["body"], "oversized body must be trimmed"
    assert chunks[0][0]["uid"] == "1"
    assert run_summary._prompt_bytes_for(chunks[0], payload, "/tmp/note.md") <= run_summary.PI_MAX_PROMPT_BYTES


def test_error_report_prefers_the_real_backend_error_over_startup_noise(tmp_path: Path, monkeypatch) -> None:
    """stderr starts with unrelated startup noise; the actual error must be reported."""
    payload_path = tmp_path / "payloads" / "sample.json"
    _write_payload(payload_path)

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = (
                "[tapd-cli-env] 已注入 7 个变量（TAPD_API_ENDPOINT 已设置）\n"
                'Warning: Extension package "builtin:mcp": ... not loaded.\n'
                '400: {"code":"1261","message":"Prompt 超长"}'
            )

        return Result()

    monkeypatch.setattr("run_summary.subprocess.run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        summarize_payload(
            payload_path=payload_path,
            runtime_config={"obsidian_output_dir": str(tmp_path / "notes")},
            dry_run=False,
        )

    message = str(excinfo.value)
    assert "Prompt 超长" in message
    assert "tapd-cli-env" not in message
    assert "not loaded" not in message
