from ..core.supabase_client import get_supabase_client


def create_history_entry(
    card_code: str,
    card_name: str | None,
    status: str,
    source: str = "manual",
    telegram_message_id: int | None = None,
    target_chat_id: str | None = None,
    raw: dict | None = None,
) -> None:
    client = get_supabase_client()
    if not client:
        return
    row: dict = {
        "card_code": card_code,
        "card_name": card_name,
        "status": status,
        "source": source,
    }
    if telegram_message_id is not None:
        row["telegram_message_id"] = telegram_message_id
    if target_chat_id is not None:
        row["target_chat_id"] = target_chat_id
    if raw is not None:
        row["raw"] = raw
    client.post("bot_posting_history", row, prefer="return=minimal")
