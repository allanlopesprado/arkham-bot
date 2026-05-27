from ..supabase_client import get_supabase_client


def get_admin(telegram_user_id: int) -> dict | None:
    client = get_supabase_client()
    if not client:
        return None
    rows = client.get("bot_admins", {"telegram_user_id": f"eq.{telegram_user_id}", "enabled": "eq.true", "limit": "1"})
    return rows[0] if rows else None
