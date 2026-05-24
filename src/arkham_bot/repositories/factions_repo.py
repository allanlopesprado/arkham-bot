from ..supabase_client import get_supabase_client


def upsert_faction(faction: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"code": faction.get("code"), "name": faction.get("name"), "raw": faction}
    client.upsert("arkham_factions", row, on_conflict="code")
