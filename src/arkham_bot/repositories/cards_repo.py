import re

from ..supabase_client import get_supabase_client

_PAGE = 1000


def upsert_card(card: dict) -> None:
    """Upsert a card from the original ArkhamDB JSON. All schema columns are populated."""
    client = get_supabase_client()
    if not client:
        return
    row = {
        # Identity
        "code": card.get("code"),
        "name": card.get("name") or card.get("real_name"),
        "real_name": card.get("real_name"),
        # Classification
        "type_code": card.get("type_code"),
        "subtype_code": card.get("subtype_code"),
        "faction_code": card.get("faction_code"),
        "faction_name": card.get("faction_name"),
        "pack_code": card.get("pack_code"),
        "pack_name": card.get("pack_name"),
        # Deck
        "position": card.get("position"),
        "quantity": card.get("quantity"),
        "xp": card.get("xp"),
        "cost": card.get("cost"),
        "is_unique": card.get("is_unique"),
        "is_exceptional": card.get("exceptional") or card.get("is_exceptional"),
        "deck_limit": card.get("deck_limit"),
        # Text
        "text": card.get("text"),
        "real_text": card.get("real_text"),
        "flavor": card.get("flavor"),
        "traits": card.get("traits"),
        # Back side (double-sided cards / investigators)
        "double_sided": bool(card.get("double_sided")),
        "back_text": card.get("back_text"),
        "back_name": card.get("back_name"),
        "back_flavor": card.get("back_flavor"),
        # Stats
        "skill_willpower": card.get("skill_willpower"),
        "skill_intellect": card.get("skill_intellect"),
        "skill_combat": card.get("skill_combat"),
        "skill_agility": card.get("skill_agility"),
        "skill_wild": card.get("skill_wild"),
        "health": card.get("health"),
        "sanity": card.get("sanity"),
        # Images
        "imagesrc": card.get("imagesrc"),
        "backimagesrc": card.get("backimagesrc"),
        # Flags
        "spoiler": bool(card.get("spoiler")),
        # Full ArkhamDB JSON — source of truth for display
        "raw": card,
    }
    client.upsert("arkham_cards", row, on_conflict="code")


def get_card_by_code(code: str) -> dict | None:
    client = get_supabase_client()
    if not client:
        return None
    rows = client.get("arkham_cards", {"code": f"eq.{code}", "limit": "1"})
    return rows[0] if rows else None


_ENCOUNTER_TYPES = {'enemy', 'treachery', 'location', 'act', 'agenda', 'story'}


def get_all_cards(include_encounter: bool = False) -> list[dict]:
    """Returns all cards from the DB as raw ArkhamDB dicts. Paginates automatically."""
    client = get_supabase_client()
    if not client:
        return []
    results = []
    offset = 0
    while True:
        params = {
            "select": "raw,spoiler,type_code",
            "order": "code.asc",
            "limit": str(_PAGE),
            "offset": str(offset),
        }
        if not include_encounter:
            params["type_code"] = f"not.in.({','.join(_ENCOUNTER_TYPES)})"
        rows = client.get("arkham_cards", params)
        if not rows:
            break
        for row in rows:
            raw = row.get("raw")
            if not raw:
                continue
            raw["spoiler"] = bool(row.get("spoiler")) or bool(raw.get("spoiler"))
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
    safe_q = re.sub(r'[^\w\s\-]', '', q)
    results = []
    offset = 0
    while True:
        if code_prefix:
            params = {
                "select": "raw,spoiler,type_code",
                "code": f"like.{safe_q}%",
                "order": "code.asc",
                "limit": str(_PAGE),
                "offset": str(offset),
            }
        else:
            q_lower = safe_q.lower()
            params = {
                "select": "raw,spoiler,type_code",
                "or": f"(name.ilike.*{q_lower}*,real_name.ilike.*{q_lower}*)",
                "order": "code.asc",
                "limit": str(_PAGE),
                "offset": str(offset),
            }
        if not include_encounter:
            params["type_code"] = f"not.in.({','.join(_ENCOUNTER_TYPES)})"
        rows = client.get("arkham_cards", params)
        if not rows:
            break
        for row in rows:
            raw = row.get("raw")
            if not raw:
                continue
            raw["spoiler"] = bool(row.get("spoiler")) or bool(raw.get("spoiler"))
            results.append(raw)
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return results
