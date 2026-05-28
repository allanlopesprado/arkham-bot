import logging
from datetime import UTC, datetime
from html import escape

from telegram import ReplyParameters, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..core.permissions import admin_source, is_admin_user
from ..i18n import get_strings
from .common import (
    _as_bool,
    _check_rate_limit,
    _fetch_all_cards,
    _format_uptime,
    _get_cached_pack_list,
    _time_until_next_post,
)

logger = logging.getLogger(__name__)


def _format_status(payload: dict) -> str:
    s = get_strings()
    lines = [
        s["status_title"],
        "",
        s["status_date"].format(date=payload["local_date"], hour=payload["local_hour"]),
        s["status_timezone"].format(timezone=payload["timezone_name"]),
        s["status_uptime"].format(uptime=payload["uptime"]),
        "",
        s["status_cards_line"].format(count=payload["cards_count"]),
        s["status_packs_line"].format(count=payload["packs_count"]),
        s["status_taboos_line"].format(count=payload.get("taboo_count", "-")),
        "",
    ]

    if payload.get("daily_post_enabled"):
        lines.append(s["status_next_post"].format(next_post=payload.get("next_post", "-")))
    else:
        lines.append(s["status_post_disabled"])

    last_code = payload.get("last_daily_post_card_code", "-")
    last_name = payload.get("last_daily_post_card_name")
    if last_code and last_code != "-":
        display = f'<a href="https://arkhamdb.com/card/{last_code}">{escape(last_name or last_code)}</a>'
        lines.append(s["status_last_post"].format(card=display))
    else:
        lines.append(s["status_no_last_post"])

    if payload.get("is_admin"):
        lines.append("")
        lines.append(s["status_supabase"].format(status=payload.get("supabase_status", "-")))
        pending = payload.get("pending_commands", "-")
        if pending not in ("-", "0"):
            lines.append(s["status_pending_commands"].format(count=pending))

    return "\n".join(lines)


def _format_help_report() -> str:
    s = get_strings()
    lines = [
        s["help_title"], "",
        s["help_cards_section"],
        s["help_card_cmd"],
        s["help_sets_cmd"],
        s["help_search_cmd"],
        "",
        s["help_rules_section"],
        s["help_faq_cmd"],
        s["help_taboo_cmd"],
        s["help_decklist_cmd"],
        "",
        s["help_history_section"],
        s["help_cotd_cmd"],
        "",
        s["help_bot_section"],
        s["help_status_cmd"],
    ]
    return "\n".join(lines)


def _collect_status_payload(update: Update) -> dict:
    from zoneinfo import ZoneInfo

    from ..core.config import (
        AI_DAILY_CARD_ENABLED,
        AI_MODEL,
        BOT_COMMANDS_POLLING_ENABLED,
        DAILY_POST_DAYS,
        DAILY_POST_ENABLED,
        DAILY_POST_TIMES,
        DAILY_SCHEDULER_STATE_FILE,
        GEMINI_API_KEY,
        GROQ_API_KEY,
        MISTRAL_API_KEY,
        OPENAI_API_KEY,
        SUPABASE_ENABLED,
        TIMEZONE,
    )
    from ..services.local_storage import load_json_file
    from ..services.scheduler import _as_list

    user_id = update.effective_user.id if update.effective_user else None
    is_admin = is_admin_user(user_id)
    now = datetime.now(UTC)
    timezone_name = TIMEZONE
    daily_post_enabled = DAILY_POST_ENABLED
    daily_post_times = DAILY_POST_TIMES
    daily_post_days = DAILY_POST_DAYS
    supabase_status = "nao configurado"
    pending_commands = "-"
    cards_count = "-"
    packs_count = "-"
    day_config = {}

    try:
        from ..repositories.settings_repo import get_all_settings

        settings = get_all_settings()
        if SUPABASE_ENABLED:
            supabase_status = "ok"
        if settings:
            daily_post_enabled = _as_bool(settings.get("daily_post_enabled"), daily_post_enabled)
            daily_post_times = _as_list(settings.get("daily_post_times", daily_post_times), daily_post_times)
            daily_post_days = _as_list(settings.get("daily_post_days", daily_post_days), daily_post_days)
            timezone_name = str(settings.get("timezone", timezone_name) or timezone_name)
            day_config = settings.get("day_config") or {}
        else:
            day_config = {}
    except Exception as exc:
        logger.warning("status_settings_lookup_failed: %s", exc)
        supabase_status = "erro"

    taboo_count = "-"
    if SUPABASE_ENABLED:
        try:
            from ..core.supabase_client import get_supabase_client

            client = get_supabase_client()
            if client:
                cards_count = str(client.count("arkham_cards"))
                packs_count = str(client.count("arkham_packs"))
                taboo_count = str(client.count("arkham_taboos"))
        except Exception as exc:
            logger.warning("status_catalog_lookup_failed: %s", exc)
            cards_count = "erro"
            packs_count = "erro"

    if is_admin:
        try:
            from ..repositories.commands_repo import fetch_pending_commands

            pending_commands = str(len(fetch_pending_commands(50)))
        except Exception as exc:
            logger.warning("status_commands_lookup_failed: %s", exc)
            pending_commands = "erro"

    try:
        local_dt = datetime.now(ZoneInfo(timezone_name))
        local_date = local_dt.strftime("%d/%m/%Y")
        local_hour = local_dt.strftime("%H:%M")
    except Exception:
        local_dt = datetime.now()
        local_date = local_dt.strftime("%d/%m/%Y")
        local_hour = local_dt.strftime("%H:%M")

    state = load_json_file(DAILY_SCHEDULER_STATE_FILE, default={}) or {}
    last_card_code = state.get("last_daily_post_card_code", "-")

    last_card_name = None
    if last_card_code and last_card_code != "-" and SUPABASE_ENABLED:
        try:
            from ..core.supabase_client import get_supabase_client as _sc
            _client = _sc()
            if _client:
                rows = _client.get("arkham_cards", {"code": f"eq.{last_card_code}", "select": "name", "limit": "1"})
                if rows:
                    last_card_name = rows[0].get("name")
        except Exception:
            pass

    return {
        "bot": "online",
        "uptime": _format_uptime(now),
        "local_date": local_date,
        "local_hour": local_hour,
        "timezone_name": timezone_name,
        "telegram_user_id": user_id or "-",
        "daily_post_enabled": _as_bool(daily_post_enabled),
        "daily_post_times": daily_post_times,
        "daily_post_days": daily_post_days,
        "day_config": day_config,
        "last_daily_post_status": state.get("last_daily_post_status", "-"),
        "last_daily_post_card_code": last_card_code,
        "last_daily_post_card_name": last_card_name,
        "supabase_configured": SUPABASE_ENABLED,
        "supabase_status": supabase_status,
        "cards_count": f"{int(cards_count):,}".replace(",", ".") if cards_count.isdigit() else cards_count,
        "packs_count": packs_count,
        "taboo_count": taboo_count,
        "next_post": _time_until_next_post(daily_post_times, daily_post_days, timezone_name) if daily_post_enabled else "não agendado",
        "ai_daily_card_enabled": bool(AI_DAILY_CARD_ENABLED and any([GEMINI_API_KEY, OPENAI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY])),
        "ai_model": AI_MODEL or "-",
        "bot_commands_enabled": BOT_COMMANDS_POLLING_ENABLED,
        "is_admin": is_admin,
        "admin_source": admin_source(user_id),
        "pending_commands": pending_commands,
    }


async def bot_started_message(application):
    """Pre-warms card and pack caches on startup."""
    import asyncio
    try:
        logger.info("Pre-warming caches on startup...")
        await _fetch_all_cards(include_encounter=False)
        await _fetch_all_cards(include_encounter=True)
        await asyncio.to_thread(_get_cached_pack_list)
        logger.info("Cache pre-warm complete.")
    except Exception as exc:
        logger.warning("Cache pre-warm failed: %s", exc)

    logger.info("bot_startup_complete")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /status command with operational information."""
    if not await _check_rate_limit(update):
        return
    payload = _collect_status_payload(update)
    await update.message.reply_text(
        _format_status(payload),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_parameters=ReplyParameters(message_id=update.message.message_id),
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    await update.message.reply_text(
        _format_help_report(),
        parse_mode=ParseMode.HTML,
        reply_parameters=ReplyParameters(message_id=update.message.message_id),
    )
