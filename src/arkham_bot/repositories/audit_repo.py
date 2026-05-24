from ..supabase_client import get_supabase_client


def create_audit_log(action_type: str, source: str, payload: dict | None = None, result: dict | None = None, actor_telegram_user_id: int | None = None, actor_name: str | None = None) -> None:
    client = get_supabase_client()
    if not client:
        return
    client.post("audit_logs", {
        "actor_telegram_user_id": actor_telegram_user_id,
        "actor_name": actor_name,
        "action_type": action_type,
        "source": source,
        "payload": payload,
        "result": result,
    }, prefer="return=minimal")
