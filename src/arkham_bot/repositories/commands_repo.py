from datetime import datetime, timedelta, timezone

from ..core.supabase_client import get_supabase_client


def enqueue_command(
    command_type: str,
    payload: dict | None = None,
    requested_by: int | None = None,
    requested_by_name: str | None = None,
) -> dict | None:
    client = get_supabase_client()
    if not client:
        return None
    row = {
        "command_type": command_type,
        "status": "pending",
        "payload": payload or {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    if requested_by is not None:
        row["requested_by_telegram_user_id"] = requested_by
    if requested_by_name is not None:
        row["requested_by_name"] = requested_by_name
    rows = client.post("bot_commands", row, prefer="return=representation")
    return rows[0] if rows else None


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


def recover_stale_processing_commands(timeout_seconds: int, retry_delay_seconds: int) -> dict[str, int]:
    client = get_supabase_client()
    if not client:
        return {"retrying": 0, "failed": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
    rows = client.get(
        "bot_commands",
        {
            "status": "eq.processing",
            "executed_at": "is.null",
            "updated_at": f"lt.{cutoff.isoformat()}",
        },
    )
    recovered = {"retrying": 0, "failed": 0}
    for row in rows:
        command_id = row.get("id")
        if not command_id:
            continue
        attempt_count = int(row.get("attempt_count") or 0)
        max_attempts = int(row.get("max_attempts") or 3)
        error = f"Recovered stale processing command after {timeout_seconds}s timeout"
        result = {"error": error, "recovered_from": "processing", "attempt_count": attempt_count, "max_attempts": max_attempts}
        if attempt_count < max_attempts:
            mark_command_retrying(command_id, error, retry_delay_seconds, result=result)
            recovered["retrying"] += 1
        else:
            mark_command_failed(command_id, error, result=result)
            recovered["failed"] += 1
    return recovered


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
