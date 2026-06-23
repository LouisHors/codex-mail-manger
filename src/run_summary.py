from __future__ import annotations

import subprocess
import json
from pathlib import Path

from prompt_builder import write_prompt_artifacts
from runtime import ensure_runtime_layout, load_runtime_config, load_state


def summarize_payload(payload_path: Path, runtime_config: dict, dry_run: bool) -> dict:
    payload = json.loads(payload_path.read_text())
    output_dir = payload_path.parents[1] / "output"
    prompt_path, manifest_path = write_prompt_artifacts(
        payload,
        output_dir=output_dir,
        obsidian_note_path=_daily_note_path(runtime_config),
    )
    summary_path = output_dir / f"{prompt_path.stem.replace('-prompt', '')}-summary.md"

    if dry_run:
        summary_markdown = "\n".join(
            [
                "# 快速概览",
                f"本次发现 {len(payload['messages'])} 封新邮件。",
                "",
                "# 需要关注",
                "- dry-run",
                "",
                "# 可能需要回复",
                "- dry-run",
                "",
                "# 重要邮件详情",
                "- dry-run",
                "",
                "# 运行元数据",
                f"- prompt: {prompt_path}",
            ]
        )
        summary_path.write_text(summary_markdown)
        return {
            "summary_markdown": summary_markdown,
            "prompt_path": str(prompt_path),
            "manifest_path": str(manifest_path),
            "summary_path": str(summary_path),
        }

    subprocess.run(
        [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--output-last-message",
            str(summary_path),
            "-",
        ],
        input=prompt_path.read_text(),
        text=True,
        check=True,
    )
    summary_markdown = summary_path.read_text()
    return {
        "summary_markdown": summary_markdown,
        "prompt_path": str(prompt_path),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
    }


def _daily_note_path(runtime_config: dict) -> str:
    from datetime import datetime

    return str(Path(runtime_config["obsidian_output_dir"]) / f"{datetime.now().strftime('%Y-%m-%d')}.md")


def run_summary_cli(root: Path, preview: bool, payload_path: Path | None) -> dict:
    from datetime import datetime, timezone

    ensure_runtime_layout(root)
    runtime_config = load_runtime_config(root / "config" / "runtime.json")

    resolved_payload_path = payload_path
    if resolved_payload_path is None:
        payload_dir = root / "payloads"
        payload_dir.mkdir(parents=True, exist_ok=True)
        resolved_payload_path = payload_dir / "preview-payload.json"
        state = load_state(root / "state" / "last_success.json")
        payload = {
            "window": {
                "from": state.get("last_success_at") or datetime.now(timezone.utc).isoformat(),
                "to": datetime.now(timezone.utc).isoformat(),
            },
            "messages": [
                {
                    "uid": "preview-001",
                    "subject": "Preview message",
                    "from": {"name": "Preview Sender", "email": "preview@example.com"},
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "body": "This is a preview message for prompt generation.",
                }
            ],
        }
        resolved_payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    return summarize_payload(
        payload_path=resolved_payload_path,
        runtime_config=runtime_config,
        dry_run=preview,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--payload", type=Path)
    args = parser.parse_args()

    result = run_summary_cli(root=args.root, preview=args.preview, payload_path=args.payload)
    print(result["summary_markdown"])
