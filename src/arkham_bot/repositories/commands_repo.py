from datetime import datetime, timedelta, timezone

from ..supabase_client import get_supabase_client


def fetch_pending_commands(limit: int = 10) -> list[dict]:
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get(
        "bot_commands",
        {
            "or": "(status.eq.pending,status.eq.retrying)",
            "order": "created_at.asc",
            "limit": str(limit * 3),
        },
    )
    now = datetime.now(timezone.utc)
    due: list[dict] = []
    for row in rows:
        scheduled_for = _parse_dt(row.get("scheduled_for"))
        next_attempt_at = _parse_dt(row.get("next_attempt_at"))
        if scheduled_for and scheduled_for > now:
            continue
        if row.get("status") == "retrying" and next_attempt_at and next_attempt_at > now:
            continue
        due.append(row)
        if len(due) >= limit:
            break
    return due


def mark_command_processing(command_id: str, attempt_count: int | None = None) -> None:
    payload = {"status": "processing", "updated_at": _now()}
    if attempt_count is not None:
        payload["attempt_count"] = attempt_count
    _patch_status(command_id, payload)


def mark_command_executed(command_id: str, result: dict | None = None) -> None:
    payload = {"status": "executed", "executed_at": _now(), "updated_at": _now(), "last_error": None, "next_attempt_at": None}
    if result is not None:
        payload["result"] = result
    _patch_status(command_id, payload)


def mark_command_failed(command_id: str, error: str, result: dict | None = None) -> None:
    payload = {"status": "failed", "last_error": error, "updated_at": _now()}
    if result is not None:
        payload["result"] = result
    _patch_status(command_id, payload)


def mark_command_retrying(command_id: str, error: str, delay_seconds: int, result: dict | None = None) -> None:
    next_attempt = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    payload = {
        "status": "retrying",
        "last_error": error,
        "next_attempt_at": next_attempt.isoformat(),
        "updated_at": _now(),
    }
    if result is not None:
        payload["result"] = result
    _patch_status(command_id, payload)


def cancel_pending_commands(reason: str = "cancelled") -> int:
    client = get_supabase_client()
    if not client:
        return 0
    rows = client.get("bot_commands", {"or": "(status.eq.pending,status.eq.retrying)", "select": "id"})
    for row in rows:
        _patch_status(row["id"], {"status": "cancelled", "last_error": reason, "updated_at": _now()})
    return len(rows)


def _patch_status(command_id: str, payload: dict) -> None:
    client = get_supabase_client()
    if client:
        client.patch("bot_commands", payload, {"id": f"eq.{command_id}"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None
