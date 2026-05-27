from ..core.supabase_client import get_supabase_client


def upsert_taboo(taboo_id: str, payload: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"taboo_id": taboo_id, "raw": payload}
    client.upsert("arkham_taboos", row, on_conflict="taboo_id")


def get_all_taboos() -> list[dict]:
    """Returns all taboo lists as raw ArkhamDB dicts, sorted newest first."""
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get("arkham_taboos", {"select": "raw", "order": "taboo_id.desc"})
    return [r["raw"] for r in rows if r.get("raw")]
