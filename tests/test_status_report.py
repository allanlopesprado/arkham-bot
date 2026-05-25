from datetime import UTC, datetime, timedelta

from arkham_bot import telegram_handlers


def test_format_status_report_includes_operational_fields():
    payload = {
        "bot": "online",
        "uptime": "2h 3m",
        "local_time": "2026-05-25 10:00:00 -03",
        "telegram_chat_configured": True,
        "telegram_user_id": 206091852,
        "daily_post_enabled": True,
        "daily_post_times": ["08:00"],
        "daily_post_days": ["mon", "tue"],
        "last_daily_post_status": "success",
        "last_daily_post_card_code": "01001",
        "supabase_configured": True,
        "supabase_status": "ok",
        "bot_commands_enabled": True,
        "is_admin": True,
        "admin_source": "owner",
        "pending_commands": "0",
    }

    text = telegram_handlers._format_status_report(payload)

    assert "Arkham Bot - Status" in text
    assert "Postagem diaria" in text
    assert "Supabase leitura: ok" in text
    assert "Comandos pendentes/retry: 0" in text


def test_format_status_report_escapes_values():
    payload = {
        "bot": "online<script>",
        "uptime": "0m",
        "local_time": "now",
        "telegram_chat_configured": False,
        "telegram_user_id": "<id>",
        "daily_post_enabled": False,
        "daily_post_times": ["<08:00>"],
        "daily_post_days": ["mon"],
        "last_daily_post_status": "<failed>",
        "last_daily_post_card_code": "01001",
        "supabase_configured": False,
        "supabase_status": "nao configurado",
        "bot_commands_enabled": False,
        "is_admin": False,
        "admin_source": "none",
        "pending_commands": "-",
    }

    text = telegram_handlers._format_status_report(payload)

    assert "online&lt;script&gt;" in text
    assert "&lt;id&gt;" in text
    assert "<failed>" not in text


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
