from ..supabase_client import get_supabase_client


def upsert_pack(pack: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"code": pack.get("code"), "name": pack.get("name"), "raw": pack}
    client.upsert("arkham_packs", row, on_conflict="code")
