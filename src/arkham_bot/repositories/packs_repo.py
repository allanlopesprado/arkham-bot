from ..supabase_client import get_supabase_client


def upsert_pack(payload: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    client.upsert("arkham_packs", {"code": payload["code"], "raw": payload}, on_conflict="code")


def get_all_packs() -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get("arkham_packs", {"select": "raw", "order": "code.asc"})
    return [r["raw"] for r in rows if r.get("raw")]
