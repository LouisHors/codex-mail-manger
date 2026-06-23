from __future__ import annotations

from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime


def decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    return str(make_header(decode_header(value))).strip()


def extract_plain_text(message: Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() != "text/plain":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace").strip()
    payload = message.get_payload(decode=True) or b""
    charset = message.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace").strip()


def _normalize_addresses(value: str | None) -> list[dict[str, str]]:
    addresses = []
    for name, email in getaddresses([value or ""]):
        if not email:
            continue
        addresses.append(
            {
                "name": decode_header_value(name),
                "email": email,
            }
        )
    return addresses


def _parse_sent_at(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def normalize_message(message: Message, uid: str) -> dict[str, object]:
    from_addresses = _normalize_addresses(message.get("From"))
    return {
        "uid": uid,
        "message_id": decode_header_value(message.get("Message-ID")),
        "subject": decode_header_value(message.get("Subject")),
        "sent_at": _parse_sent_at(message.get("Date")),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "from": from_addresses[0] if from_addresses else {"name": "", "email": ""},
        "to": _normalize_addresses(message.get("To")),
        "cc": _normalize_addresses(message.get("Cc")),
        "body": extract_plain_text(message),
    }
