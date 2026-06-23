import json
from pathlib import Path

from run_summary import run_summary_cli, summarize_payload


def test_summarize_payload_non_dry_run_invokes_codex(tmp_path: Path, monkeypatch) -> None:
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
    calls = []

    def fake_run(cmd, input=None, text=None, check=None):
        calls.append(cmd)
        output_path = Path(cmd[cmd.index("--output-last-message") + 1])
        output_path.write_text("# 快速概览\n真实摘要\n\n# 需要关注\n- A\n\n# 可能需要回复\n- B\n\n# 重要邮件详情\n- C\n\n# 运行元数据\n- D")
        class Result:
            returncode = 0
        return Result()

    monkeypatch.setattr("run_summary.subprocess.run", fake_run)
    result = summarize_payload(
        payload_path=payload_path,
        runtime_config={"obsidian_output_dir": str(tmp_path / "notes")},
        dry_run=False,
    )

    assert calls
    assert result["summary_markdown"].startswith("# 快速概览")


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
