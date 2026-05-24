from ..supabase_client import get_supabase_client


def upsert_decklist(decklist_id: str, payload: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"decklist_id": decklist_id, "raw": payload}
    client.upsert("arkham_decklists_cache", row, on_conflict="decklist_id")
