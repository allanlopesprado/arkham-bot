from datetime import datetime, timedelta, timezone

from arkham_bot.repositories import commands_repo


class FakeClient:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.patches = []

    def get(self, table, params=None):
        assert table == "bot_commands"
        return self.rows

    def patch(self, table, payload, filters):
        assert table == "bot_commands"
        self.patches.append((payload, filters))
        return []


def test_fetch_pending_commands_respects_next_attempt(monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    client = FakeClient([
        {"id": "1", "status": "retrying", "next_attempt_at": future},
        {"id": "2", "status": "pending"},
    ])
    monkeypatch.setattr(commands_repo, "get_supabase_client", lambda: client)
    rows = commands_repo.fetch_pending_commands(10)
    assert [row["id"] for row in rows] == ["2"]


def test_mark_command_executed_writes_result_not_payload(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(commands_repo, "get_supabase_client", lambda: client)
    commands_repo.mark_command_executed("abc", {"ok": True})
    payload, filters = client.patches[0]
    assert payload["status"] == "executed"
    assert payload["result"] == {"ok": True}
    assert "payload" not in payload
    assert filters == {"id": "eq.abc"}


def test_recover_stale_processing_commands_retries_or_fails(monkeypatch):
    client = FakeClient([
        {"id": "retry-me", "attempt_count": 1, "max_attempts": 3},
        {"id": "fail-me", "attempt_count": 3, "max_attempts": 3},
    ])
    monkeypatch.setattr(commands_repo, "get_supabase_client", lambda: client)

    result = commands_repo.recover_stale_processing_commands(timeout_seconds=900, retry_delay_seconds=60)

    assert result == {"retrying": 1, "failed": 1}
    retry_payload, retry_filters = client.patches[0]
    fail_payload, fail_filters = client.patches[1]
    assert retry_payload["status"] == "retrying"
    assert retry_payload["result"]["recovered_from"] == "processing"
    assert retry_filters == {"id": "eq.retry-me"}
    assert fail_payload["status"] == "failed"
    assert fail_payload["result"]["recovered_from"] == "processing"
    assert fail_filters == {"id": "eq.fail-me"}
