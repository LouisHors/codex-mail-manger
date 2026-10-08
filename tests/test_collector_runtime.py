from datetime import datetime, timezone
from pathlib import Path

from collector import _fetch_mail, collect_incremental_mail


def test_collect_incremental_mail_dry_run_skips_external_fetch_and_payload_write(tmp_path: Path, monkeypatch) -> None:
    called = {"fetch": False}

    def fake_fetch(*_args, **_kwargs):
        called["fetch"] = True
        return []

    monkeypatch.setattr("collector._fetch_mail", fake_fetch)
    result = collect_incremental_mail(
        root=tmp_path,
        runtime_config={},
        state={"last_success_at": datetime(2026, 6, 23, tzinfo=timezone.utc).isoformat(), "last_processed_uids": []},
        dry_run=True,
    )

    assert called["fetch"] is False
    assert len(result["new_messages"]) == 1
    assert result["new_messages"][0]["uid"] == "dry-run-001"
    assert result["unread_count"] == 1
    assert result["payload_path"] is not None
    assert result["payload_path"].exists()


def test_fetch_mail_skips_empty_imap_fetch_items(monkeypatch) -> None:
    raw_message = (
        b"Subject: Hello\r\n"
        b"From: Sender <sender@example.com>\r\n"
        b"To: Receiver <receiver@example.com>\r\n"
        b"Date: Sat, 04 Jul 2026 09:00:00 +0800\r\n"
        b"Message-ID: <valid@example.com>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Body\r\n"
    )

    class FakeImapClient:
        def login(self, *_args):
            pass

        def select(self, *_args):
            pass

        def uid(self, command, first_arg, *args):
            if command == "search" and args == ("UNSEEN",):
                return "OK", [b"101 102"]
            if command == "search" and args == ("ALL",):
                return "OK", [b"101 102"]
            if command == "fetch" and first_arg == "101" and args == ("(RFC822)",):
                return "OK", [None]
            if command == "fetch" and first_arg == "102" and args == ("(RFC822)",):
                return "OK", [(b"102 (RFC822 {1}", raw_message)]
            raise AssertionError(f"unexpected IMAP call: {command} {first_arg} {args}")

        def logout(self):
            pass

    monkeypatch.setattr("collector.get_keychain_password", lambda *_args: "password")
    monkeypatch.setattr("collector.imaplib.IMAP4_SSL", lambda *_args: FakeImapClient())

    _unread_uids, messages = _fetch_mail(
        runtime_config={
            "keychain_account": "account@example.com",
            "keychain_service": "service",
            "imap_host": "imap.example.com",
            "imap_port": 993,
        },
        checkpoint=datetime(2026, 7, 3, tzinfo=timezone.utc),
        seen_uids=set(),
    )

    assert [message["uid"] for message in messages] == ["102"]
