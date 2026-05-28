from ..core.supabase_client import get_supabase_client


def upsert_pending(chat_id: str, chat_title: str, chat_type: str, chat_username: str | None = None) -> None:
    client = get_supabase_client()
    if not client:
        return
    client.upsert("pending_destinations", {
        "chat_id": chat_id,
        "chat_title": chat_title,
        "chat_type": chat_type,
        "chat_username": chat_username,
        "status": "pending",
    }, on_conflict="chat_id")


def dismiss_pending(chat_id: str) -> None:
    """Mark as dismissed when bot is removed from a group."""
    client = get_supabase_client()
    if not client:
        return
    try:
        client.patch("pending_destinations", {"status": "dismissed"}, {"chat_id": f"eq.{chat_id}"})
    except Exception:
        pass
