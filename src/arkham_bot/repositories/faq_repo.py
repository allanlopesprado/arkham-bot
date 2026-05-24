from ..supabase_client import get_supabase_client


def upsert_faq(card_code: str, payload) -> None:
    client = get_supabase_client()
    if not client:
        return
    row = {"card_code": card_code, "raw": payload if payload is not None else {}}
    client.upsert("arkham_faq", row, on_conflict="card_code")
