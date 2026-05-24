from ..supabase_client import get_supabase_client


def upsert_taboo(taboo_id: str, payload: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"taboo_id": taboo_id, "raw": payload}
    client.upsert("arkham_taboos", row, on_conflict="taboo_id")
