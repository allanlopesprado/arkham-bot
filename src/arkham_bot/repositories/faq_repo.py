from ..supabase_client import get_supabase_client


def upsert_faq(card_code: str, payload) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"card_code": card_code, "raw": payload if payload is not None else {}}
    client.upsert("arkham_faq", row, on_conflict="card_code")


def get_faq_by_code(card_code: str) -> list | None:
    """Returns FAQ entries for a card from the DB, or None if not found."""
    client = get_supabase_client()
    if not client:
        return None
    rows = client.get("arkham_faq", {"card_code": f"eq.{card_code}", "select": "raw", "limit": "1"})
    if not rows:
        return None
    raw = rows[0].get("raw")
    if raw is None:
        return None
    return raw if isinstance(raw, list) else [raw]
