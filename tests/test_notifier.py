from pathlib import Path

import notifier


def test_send_notification_skips_when_terminal_notifier_missing(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(notifier, "which", lambda _name: None)
    monkeypatch.setattr(notifier.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    notifier.send_notification("Title", "Message")

    assert calls == []


def test_send_notification_uses_resolved_terminal_notifier(monkeypatch, tmp_path: Path) -> None:
    calls = []
    note_path = tmp_path / "note.md"
    note_path.write_text("# note\n")

    monkeypatch.setattr(notifier, "which", lambda _name: "/opt/homebrew/bin/terminal-notifier")
    monkeypatch.setattr(notifier.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    notifier.send_notification("Title", "Message", str(note_path))

    assert calls == [
        (
            (
                [
                    "/opt/homebrew/bin/terminal-notifier",
                    "-title",
                    "Title",
                    "-message",
                    "Message",
                    "-open",
                    f"obsidian://open?path={note_path}",
                ],
            ),
            {"check": False},
        )
    ]


def test_send_notification_passes_message_through(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(notifier, "which", lambda _name: "/opt/homebrew/bin/terminal-notifier")
    monkeypatch.setattr(notifier.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    notifier.send_notification("Mail Automation", "未读 7 / 新增 0")

    assert calls[0][0][0][4] == "未读 7 / 新增 0"
