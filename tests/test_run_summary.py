import json
from pathlib import Path

import pytest

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
