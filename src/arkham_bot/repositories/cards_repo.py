from ..supabase_client import get_supabase_client


def upsert_card(card: dict) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {
        "code": card.get("code"),
        "name": card.get("name") or card.get("real_name"),
        "real_name": card.get("real_name"),
        "type_code": card.get("type_code"),
        "faction_code": card.get("faction_code"),
        "faction_name": card.get("faction_name"),
        "pack_code": card.get("pack_code"),
        "pack_name": card.get("pack_name"),
        "position": card.get("position"),
        "xp": card.get("xp"),
        "cost": card.get("cost"),
        "text": card.get("text"),
        "real_text": card.get("real_text"),
        "traits": card.get("traits"),
        "imagesrc": card.get("imagesrc"),
        "backimagesrc": card.get("backimagesrc"),
        "spoiler": bool(card.get("spoiler")),
        "raw": card,
    }
    client.upsert("arkham_cards", row, on_conflict="code")


def get_card_by_code(code: str) -> dict | None:
    client = get_supabase_client()
    if not client:
        return None
    rows = client.get("arkham_cards", {"code": f"eq.{code}", "limit": "1"})
    return rows[0] if rows else None
