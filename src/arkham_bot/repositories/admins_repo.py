from ..supabase_client import get_supabase_client

VALID_ROLES = {"owner", "admin", "viewer"}


def get_admin(telegram_user_id: int) -> dict | None:
    client = get_supabase_client()
    if not client:
        return None
    rows = client.get("bot_admins", {"telegram_user_id": f"eq.{telegram_user_id}", "enabled": "eq.true", "limit": "1"})
    return rows[0] if rows else None


def list_admins() -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []
    return client.get("bot_admins", {"order": "created_at.asc"})


def upsert_admin(telegram_user_id: int, name: str | None = None, role: str = "admin", enabled: bool = True) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid admin role: {role}")
    client = get_supabase_client()
    if not client:
        return
    client.upsert(
        "bot_admins",
        {"telegram_user_id": telegram_user_id, "name": name, "role": role, "enabled": enabled},
        on_conflict="telegram_user_id",
    )


def disable_admin(telegram_user_id: int) -> None:
    client = get_supabase_client()
    if not client:
        return
    client.patch("bot_admins", {"enabled": False}, {"telegram_user_id": f"eq.{telegram_user_id}"})
