from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "daily_summary_prompt.md"

def build_summary_prompt(payload: dict, obsidian_note_path: str, template_path: Path = DEFAULT_TEMPLATE_PATH) -> str:
    template_text = template_path.read_text() if template_path.exists() else ""
    return "\n".join(
        [
            template_text.strip(),
            "",
            "请使用中文输出，并只返回合法 Markdown。",
            "请基于以下新邮件生成每日摘要，风格尽量果断，优先识别需要关注和可能需要回复的内容。",
            "",
            "输出必须包含以下一级标题：",
            "# 快速概览",
            "# 需要关注",
            "# 可能需要回复",
            "# 重要邮件详情",
            "# 运行元数据",
            "",
            f"同日笔记路径: {obsidian_note_path}",
            f"邮件时间窗口: {payload['window']['from']} -> {payload['window']['to']}",
            "",
            "邮件列表(JSON):",
            json.dumps(payload["messages"], ensure_ascii=False, indent=2),
        ]
    )


def write_prompt_artifacts(payload: dict, output_dir: Path, obsidian_note_path: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    prompt_path = output_dir / f"{stamp}-daily-summary-prompt.md"
    manifest_path = output_dir / f"{stamp}-daily-summary-manifest.json"

    prompt = build_summary_prompt(payload, obsidian_note_path)
    prompt_path.write_text(prompt)
    manifest = {
        "prompt_path": str(prompt_path),
        "message_count": len(payload["messages"]),
        "obsidian_note_path": obsidian_note_path,
        "window": payload["window"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return prompt_path, manifest_path
