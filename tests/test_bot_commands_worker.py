import asyncio

from arkham_bot import bot_commands_worker
from arkham_bot.daily_card import DailyPostResult


def test_post_command_uses_target_chat_id(monkeypatch):
    calls = []

    async def fake_post_daily_card(specific_card_code=None, target_chat_id=None):
        calls.append({"card_code": specific_card_code, "target_chat_id": target_chat_id})
        return DailyPostResult(True, card_code=specific_card_code, message_id=123)

    monkeypatch.setattr(bot_commands_worker, "_validate_command_authorization", lambda command: None)
    monkeypatch.setattr(bot_commands_worker, "post_daily_card", fake_post_daily_card)

    result = asyncio.run(bot_commands_worker._execute_command({
        "command_type": "post_now",
        "payload": {"card_code": "01001"},
        "target_chat_id": "-100123",
        "requested_by_telegram_user_id": 42,
    }))

    assert result == {"card_code": "01001", "message_id": 123}
    assert calls == [{"card_code": "01001", "target_chat_id": "-100123"}]
