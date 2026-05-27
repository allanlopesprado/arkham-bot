from ..core.supabase_client import get_supabase_client


def get_setting(key: str, default=None):
    client = get_supabase_client()
    if not client:
        return default
    rows = client.get("bot_settings", {"key": f"eq.{key}", "limit": "1"})
    return rows[0]["value"] if rows else default


def get_all_settings() -> dict:
    client = get_supabase_client()
    if not client:
        return {}
    return {row["key"]: row["value"] for row in client.get("bot_settings")}


def set_setting(key: str, value, description: str | None = None, updated_by: str | None = None) -> None:
    client = get_supabase_client()
    if not client:
        return
    payload = {"key": key, "value": value, "updated_by": updated_by}
    if description is not None:
        payload["description"] = description
    client.upsert("bot_settings", payload, on_conflict="key")
