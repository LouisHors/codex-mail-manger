from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from prompt_builder import build_summary_prompt, write_prompt_artifacts
from runtime import ensure_runtime_layout, load_runtime_config, load_state

DEFAULT_PI_TIMEOUT_SECONDS = 900

# pi handles a bounded amount of prompt text per call. Measured against real backlogged mail:
# ~2.8MB of prompt succeeds, while ~3.0MB silently returns empty output (exit 0, empty stdout,
# no stderr) and >=12MB fails outright with 400 {"code":"1261","message":"Prompt 超长"}.
# Stay comfortably below the cliff and summarize the backlog in several calls instead.
PI_MAX_PROMPT_BYTES = 2 * 1024 * 1024
PI_MAX_BODY_BYTES = 200 * 1024
PI_EMPTY_OUTPUT_RETRIES = 2

REQUIRED_SECTION_HEADINGS = (
    "# 快速概览",
    "# 需要关注",
    "# 可能需要回复",
    "# 重要邮件详情",
    "# 运行元数据",
)
PI_FAILURE_MARKERS = (
    "rate-limited",
    "rate_limit",
    '"type":"error"',
    "429:",
    "Error:",
)
# Startup noise pi always writes to stderr; it must never be reported as the failure reason.
PI_STDERR_NOISE_MARKERS = (
    "[tapd-cli-env]",
    "Extension package",
    "not loaded",
    "run `pi config`",
)

def summarize_payload(payload_path: Path, runtime_config: dict, dry_run: bool, note_date: str | None = None) -> dict:
    payload = json.loads(payload_path.read_text())
    output_dir = payload_path.parents[1] / "output"
    prompt_path, manifest_path = write_prompt_artifacts(
        payload,
        output_dir=output_dir,
        obsidian_note_path=_daily_note_path(runtime_config, note_date),
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

    summary_markdown = _summarize_in_chunks(payload, prompt_path, runtime_config)
    if not summary_markdown.endswith("\n"):
        summary_markdown += "\n"
    summary_path.write_text(summary_markdown)
    return {
        "summary_markdown": summary_markdown,
        "prompt_path": str(prompt_path),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
    }


def _summarize_in_chunks(payload: dict, prompt_path: Path, runtime_config: dict) -> str:
    """Summarize the payload, splitting oversized backlogs into several pi calls.

    A stalled run never advances the checkpoint, so a backlog keeps growing and the prompt
    eventually exceeds the pi prompt limit. Instead of failing forever, summarize the mail in
    prompt-bounded chunks and concatenate the section bodies.
    """
    prompt_text = prompt_path.read_text()
    if len(prompt_text.encode()) <= PI_MAX_PROMPT_BYTES:
        return _run_pi_summary(prompt_text, runtime_config)

    note_path = payload.get("obsidian_note_path", "")
    chunks = _chunk_messages(payload.get("messages", []), payload, note_path)
    section_bodies: dict[str, list[str]] = {heading: [] for heading in REQUIRED_SECTION_HEADINGS}
    for chunk in chunks:
        chunk_prompt = build_summary_prompt({**payload, "messages": chunk}, obsidian_note_path=note_path)
        chunk_markdown = _run_pi_summary(chunk_prompt, runtime_config)
        sections = _split_sections(chunk_markdown)
        for heading in REQUIRED_SECTION_HEADINGS:
            body = sections.get(heading, "").strip()
            if body:
                section_bodies[heading].append(body)

    return _merge_sections(section_bodies, chunk_count=len(chunks))


def _prompt_bytes_for(messages: list[dict], payload: dict, note_path: str) -> int:
    """Measure the prompt bytes exactly as pi will receive them.

    The prompt embeds the messages with `indent=2`, so measuring compact JSON would
    underestimate the real payload and let a chunk drift past the pi size limit.
    """
    return len(build_summary_prompt({**payload, "messages": messages}, obsidian_note_path=note_path).encode())

def _chunk_messages(messages: list[dict], payload: dict | None = None, note_path: str = "") -> list[list[dict]]:
    """Group messages so each chunk's rendered prompt stays within the pi size limit."""
    payload = payload or {}
    chunks: list[list[dict]] = []
    current: list[dict] = []

    for message in messages:
        candidate = [*current, _trim_message(message)]
        if current and _prompt_bytes_for(candidate, payload, note_path) > PI_MAX_PROMPT_BYTES:
            chunks.append(current)
            candidate = [_trim_message(message)]

        # A single message may still be too large; shrink its body until it fits on its own.
        if _prompt_bytes_for(candidate, payload, note_path) > PI_MAX_PROMPT_BYTES:
            candidate = [_shrink_message_to_fit(message, payload, note_path)]

        current = candidate

    if current:
        chunks.append(current)
    return chunks or [[]]


def _shrink_message_to_fit(message: dict, payload: dict, note_path: str) -> dict:
    """Halve a message body until its rendered prompt fits, so no chunk can exceed the limit."""
    limit = PI_MAX_BODY_BYTES
    while True:
        candidate = _trim_message(message, body_limit=limit)
        if _prompt_bytes_for([candidate], payload, note_path) <= PI_MAX_PROMPT_BYTES:
            return candidate
        if limit <= 1:
            # Metadata alone exceeds the budget; drop the body so the chunk can still be sent.
            candidate = _trim_message(message, body_limit=0)
            return candidate
        limit //= 8


def _trim_message(message: dict, body_limit: int = PI_MAX_BODY_BYTES) -> dict:
    body = message.get("body") or ""
    if len(body.encode()) <= body_limit:
        return dict(message)
    trimmed = dict(message)
    encoded = body.encode()[:body_limit]
    trimmed["body"] = encoded.decode("utf-8", errors="ignore") + "\n...[正文过长已截断]"
    return trimmed


def _split_sections(markdown: str) -> dict[str, str]:
    """Map each required top-level heading to the text below it."""
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped in REQUIRED_SECTION_HEADINGS:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = stripped
            buffer = []
            continue
        if current is not None:
            buffer.append(line)

    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _merge_sections(section_bodies: dict[str, list[str]], chunk_count: int) -> str:
    lines = [
        "# 快速概览",
        f"- 本次共 {chunk_count} 批邮件，已合并生成摘要。",
        "",
    ]
    for heading in REQUIRED_SECTION_HEADINGS:
        if heading == "# 快速概览":
            continue
        lines.append(heading)
        bodies = section_bodies.get(heading) or ["- 无"]
        for body in bodies:
            lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _run_pi_summary(prompt_text: str, runtime_config: dict) -> str:
    """Run the pi agent in non-interactive mode and validate its Markdown output.

    `pi -p` reads the prompt from stdin and writes the answer to stdout. It can exit 0
    even when the backend fails (for example HTTP 429 rate limiting, or a prompt near the
    size limit that yields empty output), so the stdout payload is validated instead of
    trusting the exit code. Empty output is retried because it has been observed as a
    transient, fast failure.
    """
    attempts = int(runtime_config.get("pi_empty_output_retries", PI_EMPTY_OUTPUT_RETRIES))
    last_error: RuntimeError | None = None

    for attempt in range(attempts + 1):
        try:
            return _invoke_pi(prompt_text, runtime_config)
        except RuntimeError as exc:
            last_error = exc
            if "empty output" not in str(exc) or attempt >= attempts:
                raise
            time.sleep(2 ** attempt)

    raise last_error if last_error else RuntimeError("pi failed without an error")


def _invoke_pi(prompt_text: str, runtime_config: dict) -> str:
    """Perform a single pi invocation and return its validated Markdown output."""
    executable = runtime_config.get("pi_executable") or shutil.which("pi") or "pi"
    command = [
        executable,
        "-p",
        "--no-tools",
        "--no-session",
        "--no-context-files",
    ]
    model = runtime_config.get("pi_model")
    if model:
        command.extend(["--model", model])

    try:
        completed = subprocess.run(
            command,
            input=prompt_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=runtime_config.get("pi_timeout_seconds", DEFAULT_PI_TIMEOUT_SECONDS),
            env=_pi_env(),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"pi executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"pi timed out after {exc.timeout}s") from exc

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(
            f"pi exited with status {completed.returncode}: {_pi_error_hint(stderr, stdout)}"
        )
    if not stdout:
        raise RuntimeError(f"pi returned empty output: {_pi_error_hint(stderr, stdout)}")
    if any(marker in stdout for marker in PI_FAILURE_MARKERS) and not stdout.lstrip().startswith("#"):
        raise RuntimeError(f"pi returned an error payload instead of Markdown: {_first_line(stdout)}")
    if not stdout.lstrip().startswith("#"):
        raise RuntimeError(f"pi output is not Markdown: {_first_line(stdout)}")

    missing = [heading for heading in REQUIRED_SECTION_HEADINGS if heading not in stdout]
    if missing:
        raise RuntimeError(f"pi output is missing required sections: {', '.join(missing)}")
    return stdout

def _pi_env() -> dict:
    env = dict(os.environ)
    extra_paths = [str(Path.home() / "bin"), "/opt/homebrew/bin", "/usr/local/bin"]
    existing = env.get("PATH", "")
    env["PATH"] = os.pathsep.join([path for path in extra_paths + [existing] if path])
    return env


def _first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""


def _pi_error_hint(stderr: str, stdout: str) -> str:
    """Pick the most informative error line, skipping pi's startup noise."""
    for line in (stderr or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(marker in stripped for marker in PI_STDERR_NOISE_MARKERS):
            continue
        return stripped
    return _first_line(stdout) or "no error output"


def _daily_note_path(runtime_config: dict, note_date: str | None = None) -> str:
    from datetime import datetime

    stamp = note_date or datetime.now().strftime("%Y-%m-%d")
    return str(Path(runtime_config["obsidian_output_dir"]) / f"{stamp}.md")


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
