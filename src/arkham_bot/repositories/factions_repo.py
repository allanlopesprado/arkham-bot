from ..supabase_client import get_supabase_client


def upsert_faction(payload: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    client.upsert("arkham_factions", {"code": payload["code"], "name": payload.get("name", ""), "raw": payload}, on_conflict="code")
