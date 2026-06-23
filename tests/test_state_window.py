from datetime import datetime, timedelta, timezone

from collector import filter_new_messages


def test_filter_new_messages_keeps_only_messages_after_checkpoint() -> None:
    checkpoint = datetime(2026, 6, 22, 1, 0, tzinfo=timezone.utc)
    messages = [
        {"uid": "100", "sent_at": "2026-06-22T00:59:59+00:00"},
        {"uid": "101", "sent_at": "2026-06-22T01:00:01+00:00"},
        {"uid": "102", "sent_at": "2026-06-23T01:15:00+00:00"},
    ]

    filtered = filter_new_messages(messages, checkpoint, seen_uids=set())

    assert [message["uid"] for message in filtered] == ["101", "102"]


def test_filter_new_messages_deduplicates_previously_seen_uids() -> None:
    checkpoint = datetime.now(timezone.utc) - timedelta(days=1)
    messages = [
        {"uid": "201", "sent_at": "2026-06-23T01:15:00+00:00"},
        {"uid": "202", "sent_at": "2026-06-23T02:15:00+00:00"},
    ]

    filtered = filter_new_messages(messages, checkpoint, seen_uids={"201"})

    assert [message["uid"] for message in filtered] == ["202"]
