import logging

from ..core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

VALID_SOURCES = frozenset({
    "telegram_command", "telegram_button", "mini_app",
    "system_job", "ai_process", "github_deploy", "manual_script",
})


def create_audit_log(
    action_type: str,
    source: str,
    payload: dict | None = None,
    result: dict | None = None,
    actor_telegram_user_id: int | None = None,
    actor_name: str | None = None,
) -> None:
    if source not in VALID_SOURCES:
        logger.warning(f"audit_log invalid source={source!r}, defaulting to 'system_job'")
        source = "system_job"
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
