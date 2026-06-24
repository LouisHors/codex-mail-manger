from datetime import datetime, timezone
from pathlib import Path

from collector import collect_incremental_mail


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
