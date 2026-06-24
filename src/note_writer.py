from __future__ import annotations

import json
from pathlib import Path


FOOTER_MARKER = "<!-- MAILAUTOMATION_STATE"
FOOTER_END = "MAILAUTOMATION_STATE -->"


def update_daily_note(
    note_path: Path,
    summary_markdown: str,
    checkpoint: dict,
    run_timestamp: str,
    unread_count: int,
    new_message_count: int,
) -> dict:
    overview = _compose_overview(summary_markdown, unread_count, new_message_count)
    run_block = _compose_run_block(run_timestamp, summary_markdown, unread_count, new_message_count)
    footer = f"{FOOTER_MARKER}\n{json.dumps(checkpoint, ensure_ascii=False)}\n{FOOTER_END}"

    if note_path.exists():
        existing = note_path.read_text()
        runs = _extract_runs(existing)
    else:
        note_path.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
        runs = []

    runs.insert(0, run_block)
    content = "\n".join(
        [
            f"# {note_path.stem}",
            "",
            "## 快速概览",
            overview,
            "",
            "## Runs",
            "",
            "\n".join(runs).strip(),
            "",
            footer,
            "",
        ]
    )
    note_path.write_text(content)
    return {"updated": True, "path": str(note_path)}


def _compose_overview(summary_markdown: str, unread_count: int, new_message_count: int) -> str:
    base_overview = _extract_section(summary_markdown, "快速概览")
    lines = [
        f"- 当前未读：{unread_count}",
        f"- 本次新增：{new_message_count}",
    ]
    if base_overview:
        lines.append(base_overview)
    elif new_message_count == 0:
        lines.append("本次无新增邮件，未刷新摘要内容。")
    return "\n".join(lines)


def _compose_run_block(
    run_timestamp: str,
    summary_markdown: str,
    unread_count: int,
    new_message_count: int,
) -> str:
    metric_lines = [
        f"### Run {run_timestamp}",
        "",
        f"- 当前未读：{unread_count}",
        f"- 本次新增：{new_message_count}",
        "",
    ]
    if new_message_count == 0:
        metric_lines.append("本次无新增邮件，未刷新摘要内容。")
        return "\n".join(metric_lines).strip() + "\n"
    metric_lines.append(summary_markdown.strip())
    return "\n".join(metric_lines).strip() + "\n"


def _extract_section(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    target = f"# {title}"
    capture = []
    found = False
    for line in lines:
        if line.startswith("# ") and found and line != target:
            break
        if found:
            capture.append(line)
        if line == target:
            found = True
    return "\n".join(capture).strip()


def _extract_runs(content: str) -> list[str]:
    if "## Runs" not in content:
        return []
    after_runs = content.split("## Runs", 1)[1]
    before_footer = after_runs.split(FOOTER_MARKER, 1)[0]
    blocks = [block.strip() for block in before_footer.split("### Run ") if block.strip()]
    cleaned = []
    for block in blocks:
        lines = block.splitlines()
        timestamp = lines[0].strip()
        body_lines = []
        inside_overview = False
        for line in lines[1:]:
            if line == "# 快速概览":
                inside_overview = True
                continue
            if inside_overview and line.startswith("# "):
                inside_overview = False
            if inside_overview:
                continue
            body_lines.append(line)
        cleaned.append(f"### Run {timestamp}\n" + "\n".join(body_lines).strip())
    return cleaned


if __name__ == "__main__":
    import argparse
    import json
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--note-path", type=Path)
    args = parser.parse_args()

    if not args.sample:
        raise SystemExit("Use --sample to generate a sample note update.")

    note_path = args.note_path or (Path(__file__).resolve().parents[1] / "output" / "sample-note.md")
    summary_markdown = "\n".join(
        [
            "# 快速概览",
            "示例：今天有 1 封需要关注的邮件。",
            "",
            "# 需要关注",
            "- 示例关注项",
            "",
            "# 可能需要回复",
            "- 示例回复项",
            "",
            "# 重要邮件详情",
            "- 示例详情",
            "",
            "# 运行元数据",
            "- 样例运行",
        ]
    )
    result = update_daily_note(
        note_path=note_path,
        summary_markdown=summary_markdown,
        checkpoint={"last_success_at": datetime.now().isoformat(), "last_processed_uids": ["sample-001"]},
        run_timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        new_message_count=1,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
