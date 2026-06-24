from __future__ import annotations

import subprocess
from shutil import which
from pathlib import Path
from urllib.parse import quote


def send_notification(title: str, message: str, open_target: str | None = None) -> None:
    terminal_notifier = which("terminal-notifier")
    if not terminal_notifier:
        return

    command = [terminal_notifier, "-title", title, "-message", message]
    if open_target:
        command.extend(["-open", _notification_open_target(open_target)])
    subprocess.run(command, check=False)


def _notification_open_target(open_target: str) -> str:
    path = Path(open_target).expanduser()
    if path.exists():
        return f"obsidian://open?path={quote(str(path))}"
    return open_target
