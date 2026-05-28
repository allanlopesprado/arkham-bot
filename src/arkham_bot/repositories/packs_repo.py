from ..core.supabase_client import get_supabase_client


def upsert_pack(payload: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    record = {
        "code": payload["code"],
        "name": payload.get("name", ""),
        "raw": payload,
        "cycle_position": payload.get("cycle_position"),
        "position": payload.get("position"),
        "chapter": payload.get("chapter") or 1,
        "total": payload.get("total") or 0,
    }
    client.upsert("arkham_packs", record, on_conflict="code")
