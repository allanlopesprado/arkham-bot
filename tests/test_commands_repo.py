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
