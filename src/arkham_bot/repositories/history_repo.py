from ..supabase_client import get_supabase_client


def create_history_entry(entry: dict) -> None:
    client = get_supabase_client()
    if client:
        client.post("bot_posting_history", entry, prefer="return=minimal")
