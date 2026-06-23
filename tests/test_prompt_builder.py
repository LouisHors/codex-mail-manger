import json
from pathlib import Path

from prompt_builder import DEFAULT_TEMPLATE_PATH, build_summary_prompt, write_prompt_artifacts


def sample_payload() -> dict:
    return {
        "window": {
            "from": "2026-06-23T00:00:00+00:00",
            "to": "2026-06-23T01:00:00+00:00",
        },
        "messages": [
            {
                "uid": "1001",
                "subject": "Project Alpha update",
                "from": {"name": "Alice", "email": "alice@example.com"},
                "sent_at": "2026-06-23T00:15:00+00:00",
                "body": "Need your approval today.",
            }
        ],
    }


def test_build_summary_prompt_includes_required_sections_and_messages() -> None:
    prompt = build_summary_prompt(
        sample_payload(),
        obsidian_note_path="/tmp/2026-06-23.md",
    )

    assert "请使用中文输出" in prompt
    assert "快速概览" in prompt
    assert "需要关注" in prompt
    assert "可能需要回复" in prompt
    assert "重要邮件详情" in prompt
    assert "运行元数据" in prompt
    assert "Project Alpha update" in prompt
    assert "/tmp/2026-06-23.md" in prompt


def test_write_prompt_artifacts_persists_prompt_and_manifest(tmp_path: Path) -> None:
    prompt_path, manifest_path = write_prompt_artifacts(
        sample_payload(),
        output_dir=tmp_path,
        obsidian_note_path="/tmp/2026-06-23.md",
    )

    assert prompt_path.exists()
    assert manifest_path.exists()
    assert "Project Alpha update" in prompt_path.read_text()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["prompt_path"] == str(prompt_path)
    assert manifest["message_count"] == 1
    assert manifest["obsidian_note_path"] == "/tmp/2026-06-23.md"


def test_build_summary_prompt_uses_template_contract_headings() -> None:
    prompt = build_summary_prompt(
        sample_payload(),
        obsidian_note_path="/tmp/2026-06-23.md",
        template_path=DEFAULT_TEMPLATE_PATH,
    )

    template_text = DEFAULT_TEMPLATE_PATH.read_text()
    assert "# Daily Summary Prompt Contract" in template_text
    assert "Behavior notes:" in prompt
