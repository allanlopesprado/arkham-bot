from datetime import UTC, datetime, timedelta

from arkham_bot import telegram_handlers


def test_format_status_includes_key_fields():
    payload = {
        "uptime": "2h 3m",
        "cards_count": "1234",
    }

    text = telegram_handlers._format_status(payload)

    assert "Online" in text
    assert "2h 3m" in text
    assert "1234" in text


def test_format_uptime_is_compact(monkeypatch):
    started_at = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    monkeypatch.setattr(telegram_handlers, "BOT_STARTED_AT", started_at)

    assert telegram_handlers._format_uptime(started_at + timedelta(minutes=7)) == "7m"
    assert telegram_handlers._format_uptime(started_at + timedelta(hours=2, minutes=4)) == "2h 4m"
    assert telegram_handlers._format_uptime(started_at + timedelta(days=1, hours=3, minutes=9)) == "1d 3h 9m"


def test_as_bool_understands_string_settings():
    assert telegram_handlers._as_bool("true") is True
    assert telegram_handlers._as_bool("sim") is True
    assert telegram_handlers._as_bool("false", True) is False
    assert telegram_handlers._as_bool(None, True) is True


def test_format_help_report_is_structured():
    text = telegram_handlers._format_help_report()

    assert "<b>Cartas</b>" in text
    assert "<code>/status</code>" in text
    assert "<b>Admin</b>" not in text
