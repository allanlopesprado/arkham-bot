from ..supabase_client import get_supabase_client


def list_recent_errors(limit: int = 10) -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []
    return client.get("bot_errors", {"order": "created_at.desc", "limit": str(limit)})
