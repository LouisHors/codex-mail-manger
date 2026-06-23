from pathlib import Path

from note_writer import update_daily_note


def sample_summary(overview: str, run_label: str) -> str:
    return "\n".join(
        [
            "# 快速概览",
            overview,
            "",
            "# 需要关注",
            "- 跟进审批",
            "",
            "# 可能需要回复",
            "- 回复 Alice",
            "",
            "# 重要邮件详情",
            f"- {run_label}",
            "",
            "# 运行元数据",
            "- 新邮件数: 1",
        ]
    )


def test_update_daily_note_creates_new_note_with_footer(tmp_path: Path) -> None:
    note_path = tmp_path / "2026-06-23.md"

    result = update_daily_note(
        note_path=note_path,
        summary_markdown=sample_summary("今早有 1 封关键邮件。", "run-1"),
        checkpoint={"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": ["1001"]},
        run_timestamp="2026-06-23T09:30:00+08:00",
        new_message_count=1,
    )

    content = note_path.read_text()
    assert result["updated"] is True
    assert "今早有 1 封关键邮件。" in content
    assert "### Run 2026-06-23T09:30:00+08:00" in content
    assert '"last_processed_uids": ["1001"]' in content


def test_update_daily_note_replaces_overview_and_appends_run_section(tmp_path: Path) -> None:
    note_path = tmp_path / "2026-06-23.md"
    update_daily_note(
        note_path=note_path,
        summary_markdown=sample_summary("第一次概览。", "run-1"),
        checkpoint={"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": ["1001"]},
        run_timestamp="2026-06-23T09:30:00+08:00",
        new_message_count=1,
    )

    update_daily_note(
        note_path=note_path,
        summary_markdown=sample_summary("第二次概览。", "run-2"),
        checkpoint={"last_success_at": "2026-06-23T06:00:00+00:00", "last_processed_uids": ["1001", "1002"]},
        run_timestamp="2026-06-23T15:30:00+08:00",
        new_message_count=1,
    )

    content = note_path.read_text()
    assert "第二次概览。" in content
    assert "第一次概览。" not in content
    assert content.count("### Run ") == 2
    assert "run-1" in content
    assert "run-2" in content


def test_update_daily_note_skips_write_when_no_new_mail(tmp_path: Path) -> None:
    note_path = tmp_path / "2026-06-23.md"

    result = update_daily_note(
        note_path=note_path,
        summary_markdown=sample_summary("不会写入。", "run-0"),
        checkpoint={"last_success_at": "2026-06-23T01:00:00+00:00", "last_processed_uids": []},
        run_timestamp="2026-06-23T09:30:00+08:00",
        new_message_count=0,
    )

    assert result == {"updated": False, "path": str(note_path)}
    assert not note_path.exists()
