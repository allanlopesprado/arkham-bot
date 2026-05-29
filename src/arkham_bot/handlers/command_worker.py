import asyncio
import logging
from typing import Any

from telegram import Bot
from telegram.error import TelegramError

from ..core.config import (
    ADMIN_TELEGRAM_USER_IDS,
    BOT_COMMANDS_BATCH_SIZE,
    BOT_COMMANDS_MAX_RETRIES,
    BOT_COMMANDS_POLLING_INTERVAL_SECONDS,
    BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS,
    BOT_COMMANDS_RETRY_DELAY_SECONDS,
    POSTED_CARDS_FILE,
    POSTED_CARDS_LOCK,
    TELEGRAM_BOT_TOKEN,
)
from ..services.daily_card import post_daily_card
from ..services.local_storage import save_posted_card, safe_atomic_write
from ..core.permissions import is_admin_user
from ..repositories.audit_repo import create_audit_log
from ..repositories.commands_repo import (
    cancel_pending_commands,
    fetch_pending_commands,
    mark_command_executed,
    mark_command_failed,
    mark_command_processing,
    mark_command_retrying,
    recover_stale_processing_commands,
)
from ..repositories.settings_repo import set_setting

logger = logging.getLogger(__name__)

ALLOWED_COMMAND_TYPES = {
    "post_now",
    "repost_card",
    "skip_card",
    "pause_daily_post",
    "resume_daily_post",
    "sync_arkhamdb",
    "clear_queue",
    "reset_cycle",
    "update_setting",
}


def _validate_command_authorization(command: dict[str, Any]) -> None:
    actor = command.get("requested_by_telegram_user_id")
    # System-created commands may omit actor. User-created commands must be admin.
    if actor is None:
        return
    try:
        actor_int = int(actor)
    except (TypeError, ValueError):
        raise PermissionError("Invalid requested_by_telegram_user_id")
    if not is_admin_user(actor_int):
        raise PermissionError(f"Telegram user {actor_int} is not allowed to execute bot command")


def _claim_commands_atomic(batch_size: int) -> list[dict]:
    """Tenta claim atômico via RPC (FOR UPDATE SKIP LOCKED) para evitar que duas instâncias
    executem o mesmo comando. Fallback automático para fetch+mark se a RPC não estiver deployada."""
    from ..core.supabase_client import get_supabase_client
    client = get_supabase_client()
    if client:
        try:
            rows = client.rpc("claim_bot_commands", {"batch_size": batch_size})
            if rows is not None:
                return rows
        except Exception:
            pass
    # Legacy fallback: fetch pending and mark processing individually
    commands = fetch_pending_commands(batch_size)
    result = []
    for command in commands:
        cid = command.get("id")
        if not cid:
            continue
        attempt_count = int(command.get("attempt_count") or 0) + 1
        mark_command_processing(cid, attempt_count=attempt_count)
        command["attempt_count"] = attempt_count
        result.append(command)
    return result


async def _notify_admins(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not ADMIN_TELEGRAM_USER_IDS:
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    for admin_id in ADMIN_TELEGRAM_USER_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text[:3900])
            await asyncio.sleep(0.5)  # respect per-chat rate limit
        except TelegramError as exc:
            logger.warning("admin_notification_failed admin_id=%s error=%s", admin_id, exc)


async def _execute_command(command: dict[str, Any]) -> dict[str, Any]:
    _validate_command_authorization(command)
    command_type = command.get("command_type")
    payload = command.get("payload") or {}

    if command_type not in ALLOWED_COMMAND_TYPES:
        raise ValueError(f"Unsupported command_type: {command_type}")

    if command_type in {"post_now", "repost_card"}:
        card_code = payload.get("card_code")
        result = await post_daily_card(
            specific_card_code=card_code,
            target_chat_id=command.get("target_chat_id"),
        )
        if not result.success:
            raise RuntimeError(result.error or f"{command_type} failed")
        return {"card_code": result.card_code, "message_id": result.message_id}

    if command_type == "skip_card":
        card_code = payload.get("card_code")
        if not card_code:
            raise ValueError("skip_card requires payload.card_code")
        save_posted_card(str(card_code))
        return {"card_code": card_code, "skipped": True}

    if command_type == "reset_cycle":
        safe_atomic_write("", POSTED_CARDS_FILE, POSTED_CARDS_LOCK, data_type="text")
        return {"cycle_reset": True}

    if command_type == "clear_queue":
        cancelled = cancel_pending_commands("clear_queue command executed")
        return {"cancelled_commands": cancelled}

    if command_type == "update_setting":
        key = payload.get("key")
        if not key:
            raise ValueError("update_setting requires payload.key")
        set_setting(str(key), payload.get("value"), updated_by=str(command.get("requested_by_telegram_user_id") or "system"))
        return {"key": key, "updated": True}

    if command_type == "pause_daily_post":
        set_setting("daily_post_enabled", False, updated_by=str(command.get("requested_by_telegram_user_id") or "system"))
        return {"daily_post_enabled": False}

    if command_type == "resume_daily_post":
        set_setting("daily_post_enabled", True, updated_by=str(command.get("requested_by_telegram_user_id") or "system"))
        return {"daily_post_enabled": True}

    if command_type == "sync_arkhamdb":
        from scripts.sync_arkhamdb import sync_arkhamdb

        sync_result = await asyncio.to_thread(sync_arkhamdb, dry_run=False, sync_faq=bool(payload.get("sync_faq", False)), faq_limit=int(payload.get("faq_limit") or 0))
        try:
            from .telegram_handlers import _cards_cache, _cards_encounter_cache
            _cards_cache.clear()
            _cards_encounter_cache.clear()
        except Exception:
            pass
        return sync_result

    raise ValueError(f"Unhandled command_type: {command_type}")


async def bot_commands_loop() -> None:
    logger.info("bot_commands_worker_started")
    while True:
        try:
            recovered = recover_stale_processing_commands(
                BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS,
                BOT_COMMANDS_RETRY_DELAY_SECONDS,
            )
            if recovered["retrying"] or recovered["failed"]:
                logger.warning("bot_commands_stale_processing_recovered: %s", recovered)

            # Use atomic RPC (FOR UPDATE SKIP LOCKED) when available, fallback to legacy
            commands = _claim_commands_atomic(BOT_COMMANDS_BATCH_SIZE)

            for command in commands:
                command_id = command.get("id")
                command_type = command.get("command_type")
                if not command_id:
                    continue
                attempt_count = int(command.get("attempt_count") or 1)
                max_attempts = int(command.get("max_attempts") or BOT_COMMANDS_MAX_RETRIES)
                try:
                    # _claim_commands_atomic já marca status=processing; não repete aqui
                    result = await _execute_command(command)
                    mark_command_executed(command_id, result)
                    create_audit_log(command_type or "unknown", "system_job", command.get("payload"), result, command.get("requested_by_telegram_user_id"), command.get("requested_by_name"))
                except Exception as exc:
                    error = str(exc)
                    logger.exception("bot_command_failed: id=%s type=%s error=%s", command_id, command_type, error)
                    result = {"error": error, "attempt_count": attempt_count, "max_attempts": max_attempts}
                    if attempt_count < max_attempts:
                        mark_command_retrying(command_id, error, delay_seconds=BOT_COMMANDS_RETRY_DELAY_SECONDS, result=result)
                    else:
                        mark_command_failed(command_id, error, result=result)
                        from ..i18n import get_strings
                        from ..repositories.settings_repo import get_setting as _gs
                        _lang = _gs("ai_language", "pt-BR")
                        _s = get_strings(_lang)
                        await _notify_admins(_s["command_failed_alert"].format(command_type=command_type or "?", attempts=attempt_count, error=error))
                    create_audit_log(command_type or "unknown", "system_job", command.get("payload"), result, command.get("requested_by_telegram_user_id"), command.get("requested_by_name"))
        except asyncio.CancelledError:
            logger.info("bot_commands_worker_stopped")
            raise
        except Exception as exc:
            logger.exception("bot_commands_worker_tick_failed: %s", exc)
        try:
            await asyncio.sleep(BOT_COMMANDS_POLLING_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("bot_commands_worker_stopped")
            raise


