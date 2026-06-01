import re
from collections import defaultdict

from ..core.config import PACK_PREFIX_LABEL_OVERRIDES
from ..core.supabase_client import get_supabase_client

_PAGE = 1000


def get_card_packs() -> list[dict]:
    """
    Returns packs grouped by 2-digit code prefix, sorted by prefix.
    Each entry: {prefix, display_name, card_count}
    Picks the shortest pack_name in each group as display name (usually the main cycle pack).
    """
    client = get_supabase_client()
    if not client:
        return []

    groups: dict[str, dict] = defaultdict(lambda: {"names": {}, "count": 0})
    offset = 0
    while True:
        rows = client.get("arkham_cards", {
            "select": "code,pack_name",
            "limit": str(_PAGE),
            "offset": str(offset),
        })
        if not rows:
            break
        for row in rows:
            code = row.get("code", "")
            pack_name = row.get("pack_name", "")
            if len(code) >= 2 and pack_name:
                prefix = code[:2]
                groups[prefix]["names"][pack_name] = groups[prefix]["names"].get(pack_name, 0) + 1
                groups[prefix]["count"] += 1
        if len(rows) < _PAGE:
            break
        offset += _PAGE

    result = []
    for prefix, data in sorted(groups.items()):
        if prefix in PACK_PREFIX_LABEL_OVERRIDES:
            best_name = PACK_PREFIX_LABEL_OVERRIDES[prefix]
        else:
            # Pick the name with the most cards; break ties by shortest name
            best_name = max(data["names"], key=lambda n: (data["names"][n], -len(n)))
        result.append({
            "prefix": prefix,
            "display_name": best_name,
            "card_count": data["count"],
        })
    return result


def _build_card_row(card: dict) -> dict:
    return {
        "code": card.get("code"),
        "name": card.get("name") or card.get("real_name"),
        "real_name": card.get("real_name"),
        "type_code": card.get("type_code"),
        "subtype_code": card.get("subtype_code"),
        "faction_code": card.get("faction_code"),
        "faction_name": card.get("faction_name"),
        "pack_code": card.get("pack_code"),
        "pack_name": card.get("pack_name"),
        "position": card.get("position"),
        "quantity": card.get("quantity"),
        "xp": card.get("xp"),
        "cost": card.get("cost"),
        "is_unique": card.get("is_unique"),
        "is_exceptional": card.get("exceptional") or card.get("is_exceptional"),
        "deck_limit": card.get("deck_limit"),
        "text": card.get("text"),
        "real_text": card.get("real_text"),
        "flavor": card.get("flavor"),
        "traits": card.get("traits"),
        "double_sided": bool(card.get("double_sided")),
        "back_text": card.get("back_text"),
        "back_name": card.get("back_name"),
        "back_flavor": card.get("back_flavor"),
        "skill_willpower": card.get("skill_willpower"),
        "skill_intellect": card.get("skill_intellect"),
        "skill_combat": card.get("skill_combat"),
        "skill_agility": card.get("skill_agility"),
        "skill_wild": card.get("skill_wild"),
        "health": card.get("health"),
        "sanity": card.get("sanity"),
        "imagesrc": card.get("imagesrc"),
        "backimagesrc": card.get("backimagesrc"),
        "spoiler": bool(card.get("spoiler")),
        "raw": card,
    }


def bulk_upsert_cards(cards: list[dict]) -> None:
    """Upsert a batch of cards in a single HTTP request."""
    client = get_supabase_client()
    if not client or not cards:
        return
    client.upsert("arkham_cards", [_build_card_row(c) for c in cards], on_conflict="code")



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


def search_cards(query: str, include_encounter: bool = True, code_prefix: bool = False, max_results: int = 100) -> list[dict]:
    """Search cards by name/real_name ilike or code prefix. Returns raw dicts."""
    client = get_supabase_client()
    if not client:
        return []
    q = query.strip()
    safe_q = re.sub(r'[^\w\s\-]', '', q).replace("_", " ").strip()
    if not safe_q:
        return []
    results = []
    offset = 0
    while True:
        page_size = max(1, min(_PAGE, max_results - len(results)))
        if code_prefix:
            params = {
                "select": "raw,spoiler,type_code",
                "code": f"like.{safe_q}%",
                "order": "code.asc",
                "limit": str(page_size),
                "offset": str(offset),
            }
        else:
            q_lower = safe_q.lower()
            params = {
                "select": "raw,spoiler,type_code",
                "or": f"(name.ilike.*{q_lower}*,real_name.ilike.*{q_lower}*)",
                "order": "code.asc",
                "limit": str(page_size),
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
            if len(results) >= max_results:
                return results
        if len(rows) < page_size:
            break
        offset += page_size
    return results
