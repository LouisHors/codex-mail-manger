from datetime import datetime, timezone
from email import message_from_bytes
from email.message import EmailMessage

from mail_parser import decode_header_value, extract_plain_text, normalize_message


def build_message() -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "=?utf-8?b?5pel5oql5oC7?="
    message["From"] = "=?utf-8?b?5byg5LiJ?= <alice@example.com>"
    message["To"] = "Bob <bob@example.com>"
    message["Cc"] = "Carol <carol@example.com>"
    message["Date"] = "Tue, 23 Jun 2026 09:15:00 +0800"
    message["Message-ID"] = "<msg-123@example.com>"
    message.set_content("Plain body line 1\nline 2\n")
    message.add_alternative("<p>HTML body</p>", subtype="html")
    return message


def test_decode_header_value_decodes_mime_words() -> None:
    assert decode_header_value("=?utf-8?b?5pel5oql5oC7?=") == "日报总"


def test_decode_header_value_falls_back_when_chinese_charset_is_misdeclared() -> None:
    assert decode_header_value("=?gb2312?b?j0A=?=") == "廆"


def test_extract_plain_text_prefers_text_plain_part() -> None:
    message = build_message()

    assert extract_plain_text(message) == "Plain body line 1\nline 2"


def test_extract_plain_text_falls_back_when_chinese_charset_is_misdeclared() -> None:
    raw_message = (
        b"Content-Type: text/plain; charset=gb2312\r\n"
        b"Content-Transfer-Encoding: base64\r\n"
        b"\r\n"
        b"j0DP7sS/uPzQwg==\r\n"
    )

    assert extract_plain_text(message_from_bytes(raw_message)) == "廆项目更新"


def test_extract_plain_text_prefers_utf8_before_chinese_compatibility_fallback() -> None:
    raw_message = (
        b"Content-Type: text/plain; charset=gb2312\r\n"
        b"Content-Transfer-Encoding: base64\r\n"
        b"\r\n"
        b"6aG555uu5pu05paw\r\n"
    )

    assert extract_plain_text(message_from_bytes(raw_message)) == "项目更新"


def test_normalize_message_preserves_addresses_and_metadata() -> None:
    message = build_message()

    normalized = normalize_message(message, uid="1001")

    assert normalized["uid"] == "1001"
    assert normalized["message_id"] == "<msg-123@example.com>"
    assert normalized["subject"] == "日报总"
    assert normalized["sent_at"] == "2026-06-23T01:15:00+00:00"
    assert normalized["from"] == {
        "name": "张三",
        "email": "alice@example.com",
    }
    assert normalized["to"] == [{"name": "Bob", "email": "bob@example.com"}]
    assert normalized["cc"] == [{"name": "Carol", "email": "carol@example.com"}]
    assert normalized["body"] == "Plain body line 1\nline 2"
    assert normalized["received_at"] <= datetime.now(timezone.utc).isoformat()
