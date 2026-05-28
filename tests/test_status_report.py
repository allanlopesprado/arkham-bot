from datetime import UTC, datetime, timedelta

from arkham_bot.handlers import telegram_handlers


def test_format_status_includes_key_fields():
    payload = {
        "uptime": "2h 3m",
        "local_date": "28/05/2026",
        "local_hour": "09:38",
        "timezone_name": "America/Sao_Paulo",
        "cards_count": "5.927",
        "packs_count": "114",
        "taboo_count": "10",
        "daily_post_enabled": True,
        "next_post": "amanhã às 08:30",
        "last_daily_post_card_code": "01001",
        "last_daily_post_card_name": "Disc of Itzamna",
        "last_daily_post_status": "success",
        "is_admin": False,
    }

    text = telegram_handlers._format_status(payload)

    assert "28/05/2026" in text
    assert "09:38" in text
    assert "2h 3m" in text
    assert "5.927" in text
    assert "114" in text
    assert "Disc of Itzamna" in text
    assert "arkhamdb.com/card/01001" in text
    assert "amanhã" in text


def test_format_uptime_is_compact(monkeypatch):
    from arkham_bot.handlers import common as _common
    started_at = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    monkeypatch.setattr(telegram_handlers, "BOT_STARTED_AT", started_at)
    monkeypatch.setattr(_common, "BOT_STARTED_AT", started_at)

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
