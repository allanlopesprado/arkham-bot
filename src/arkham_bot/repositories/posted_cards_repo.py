from ..supabase_client import get_supabase_client


def upsert_posted_card(card_code: str, telegram_message_id: int | None = None, target_chat_id: str | None = None, raw: dict | None = None) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {
        "card_code": card_code,
        "telegram_message_id": telegram_message_id,
        "target_chat_id": target_chat_id,
        "raw": raw or {},
    }
    client.upsert("bot_posted_cards", row, on_conflict="card_code")


def is_posted(card_code: str) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    rows = client.get("bot_posted_cards", {"card_code": f"eq.{card_code}", "select": "card_code", "limit": "1"})
    return bool(rows)
