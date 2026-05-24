from ..supabase_client import get_supabase_client


def create_error(context: str, error_message: str, card_code: str | None = None, raw: dict | None = None) -> None:
    client = get_supabase_client()
    if not client:
        return
    client.post(
        "bot_errors",
        {"context": context, "error_message": error_message, "card_code": card_code, "raw": raw or {}},
        prefer="return=minimal",
    )


def list_recent_errors(limit: int = 10) -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []
    return client.get("bot_errors", {"order": "created_at.desc", "limit": str(limit)})
