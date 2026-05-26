import re

from ..supabase_client import get_supabase_client

_PAGE = 1000


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


def get_all_cards(include_encounter: bool = False) -> list[dict]:
    """Returns all cards from the DB as raw ArkhamDB dicts. Paginates automatically."""
    client = get_supabase_client()
    if not client:
        return []
    # Encounter-only type codes (no player deck slot)
    ENCOUNTER_TYPES = {'enemy', 'treachery', 'location', 'act', 'agenda', 'story'}
    results = []
    offset = 0
    while True:
        rows = client.get("arkham_cards", {
            "select": "raw,spoiler",
            "order": "code.asc",
            "limit": str(_PAGE),
            "offset": str(offset),
        })
        if not rows:
            break
        for row in rows:
            raw = row.get("raw")
            if not raw:
                continue
            if not include_encounter and raw.get("type_code") in ENCOUNTER_TYPES:
                continue
            # Carry spoiler flag from DB column (may differ from raw)
            raw["spoiler"] = row.get("spoiler") or raw.get("spoiler") or False
            results.append(raw)
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return results


def search_cards(query: str, include_encounter: bool = True, code_prefix: bool = False) -> list[dict]:
    """Search cards by name/real_name ilike or code prefix. Returns raw dicts."""
    client = get_supabase_client()
    if not client:
        return []
    q = query.strip()
    ENCOUNTER_TYPES = {'enemy', 'treachery', 'location', 'act', 'agenda', 'story'}
    # Sanitize: keep only safe characters for Supabase REST filter values
    safe_q = re.sub(r'[^\w\s\-]', '', q)
    results = []
    offset = 0
    while True:
        if code_prefix:
            params = {
                "select": "raw,spoiler",
                "code": f"like.{safe_q}%",
                "order": "code.asc",
                "limit": str(_PAGE),
                "offset": str(offset),
            }
        else:
            q_lower = safe_q.lower()
            params = {
                "select": "raw,spoiler",
                "or": f"(name.ilike.*{q_lower}*,real_name.ilike.*{q_lower}*)",
                "order": "code.asc",
                "limit": str(_PAGE),
                "offset": str(offset),
            }
        rows = client.get("arkham_cards", params)
        if not rows:
            break
        for row in rows:
            raw = row.get("raw")
            if not raw:
                continue
            if not include_encounter and raw.get("type_code") in ENCOUNTER_TYPES:
                continue
            raw["spoiler"] = row.get("spoiler") or raw.get("spoiler") or False
            results.append(raw)
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return results
