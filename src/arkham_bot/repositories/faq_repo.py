from ..core.supabase_client import get_supabase_client


def get_cached_faq_codes() -> list[str]:
    """Returns card codes that already have FAQ cached in the DB."""
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get("arkham_faq", {"select": "card_code", "limit": "5000"})
    return [r["card_code"] for r in (rows or []) if r.get("card_code")]


def upsert_faq(card_code: str, payload) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"card_code": card_code, "raw": payload if payload is not None else {}}
    client.upsert("arkham_faq", row, on_conflict="card_code")


def get_faq_by_code(card_code: str) -> tuple[list | None, str | None]:
    """Returns (faq_entries, updated_at) from DB, or (None, None) if not cached."""
    client = get_supabase_client()
    if not client:
        return None, None
    rows = client.get("arkham_faq", {"card_code": f"eq.{card_code}", "select": "raw,updated_at", "limit": "1"})
    if not rows:
        return None, None
    raw = rows[0].get("raw")
    updated_at = rows[0].get("updated_at")
    if raw is None:
        return None, None
    return (raw if isinstance(raw, list) else [raw]), updated_at
