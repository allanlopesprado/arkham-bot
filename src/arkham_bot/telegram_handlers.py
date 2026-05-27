import asyncio
import io
import logging
import re
from datetime import UTC, datetime, timedelta
from html import escape
from urllib.parse import urljoin

from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import random

from .arkhamdb_client import download_image_async
from .card_provider import get_card_async
from .supabase_client import get_supabase_client
from .config import (
    BASE_URL,
    CALLBACK_CANCEL,
    CHOOSING_CARD_NUMBER,
    SEARCH_WAITING_QUERY,
    EXTENSIONS_TO_TRY,
    TELEGRAM_CHAT_ID,
)
from .permissions import admin_source, is_admin_user
from .rate_limit import rate_limiter
from .repositories.cards_repo import get_card_packs
from .text_formatters import format_card_back_caption, format_card_caption


logger = logging.getLogger(__name__)

_pack_list_cache: list[dict] = []
_pack_list_cache_ts: float = 0.0
_PACK_LIST_TTL = 3600.0  # 1 hour


def _get_cached_pack_list() -> list[dict]:
    global _pack_list_cache, _pack_list_cache_ts
    import time
    if _pack_list_cache and (time.monotonic() - _pack_list_cache_ts) < _PACK_LIST_TTL:
        return _pack_list_cache
    packs = get_card_packs()
    if packs:
        _pack_list_cache = packs
        _pack_list_cache_ts = time.monotonic()
    return _pack_list_cache
BOT_STARTED_AT = datetime.now(UTC)


async def _fetch_all_cards(include_encounter: bool = False) -> list[dict]:
    """DB-first card list fetch with API fallback."""
    from .repositories.cards_repo import get_all_cards
    from .arkhamdb_client import fetch_all_cards_sync
    try:
        cards = await asyncio.to_thread(get_all_cards, include_encounter)
        if cards:
            return cards
    except Exception as exc:
        logger.warning(f"DB get_all_cards failed: {exc}")
    logger.info("Falling back to ArkhamDB API for all cards")
    return await asyncio.to_thread(fetch_all_cards_sync, include_encounter)


async def _fetch_all_taboos() -> list[dict]:
    """DB-first taboo list fetch with API fallback."""
    from .repositories.taboos_repo import get_all_taboos
    from .arkhamdb_client import fetch_taboos_sync
    try:
        taboos = await asyncio.to_thread(get_all_taboos)
        if taboos:
            return taboos
    except Exception as exc:
        logger.warning(f"DB get_all_taboos failed: {exc}")
    logger.info("Falling back to ArkhamDB API for taboos")
    return await asyncio.to_thread(fetch_taboos_sync)


async def _fetch_faq(card_code: str) -> list | None:
    """DB-first FAQ fetch with API fallback."""
    from .repositories.faq_repo import get_faq_by_code
    from .arkhamdb_client import fetch_faq_by_card_code_sync
    try:
        faq = await asyncio.to_thread(get_faq_by_code, card_code)
        if faq is not None:
            return faq
    except Exception as exc:
        logger.warning(f"DB get_faq_by_code failed for {card_code}: {exc}")
    logger.info(f"Falling back to ArkhamDB API for FAQ {card_code}")
    return await asyncio.to_thread(fetch_faq_by_card_code_sync, card_code)

PACK_ABBREVIATIONS: dict[str, str] = {
    # Core / Revised Core
    "Core Set": "Core",
    "Revised Core Set": "rCore",
    # Dunwich Legacy
    "The Dunwich Legacy": "TDL",
    "The Dunwich Legacy Investigator Expansion": "TDL IE",
    "The Dunwich Legacy Campaign Expansion": "TDL CE",
    # Path to Carcosa
    "The Path to Carcosa": "TPC",
    "The Path to Carcosa Investigator Expansion": "TPC IE",
    "The Path to Carcosa Campaign Expansion": "TPC CE",
    # Forgotten Age
    "The Forgotten Age": "TFA",
    "The Forgotten Age Investigator Expansion": "TFA IE",
    "The Forgotten Age Campaign Expansion": "TFA CE",
    # Circle Undone
    "The Circle Undone": "TCU",
    "The Circle Undone Investigator Expansion": "TCU IE",
    "The Circle Undone Campaign Expansion": "TCU CE",
    # Dream-Eaters
    "The Dream-Eaters": "TDE",
    "The Dream-Eaters Investigator Expansion": "TDE IE",
    "The Dream-Eaters Campaign Expansion": "TDE CE",
    # Innsmouth Conspiracy
    "The Innsmouth Conspiracy": "TIC",
    "The Innsmouth Conspiracy Investigator Expansion": "TIC IE",
    "The Innsmouth Conspiracy Campaign Expansion": "TIC CE",
    # Edge of the Earth
    "Edge of the Earth": "EotE",
    "Edge of the Earth Investigator Expansion": "EotE IE",
    "Edge of the Earth Campaign Expansion": "EotE CE",
    # Scarlet Keys
    "The Scarlet Keys": "TSK",
    "The Scarlet Keys Investigator Expansion": "TSK IE",
    "The Scarlet Keys Campaign Expansion": "TSK CE",
    # Feast of Hemlock Vale
    "The Feast of Hemlock Vale": "FHV",
    "The Feast of Hemlock Vale Investigator Expansion": "FHV IE",
    "The Feast of Hemlock Vale Campaign Expansion": "FHV CE",
    # Drowned City
    "The Drowned City": "TDC",
    "The Drowned City Investigator Expansion": "TDC IE",
    "The Drowned City Campaign Expansion": "TDC CE",
    # Side stories / promos
    "Return to the Night of the Zealot": "RtNZ",
    "Return to the Dunwich Legacy": "RtDL",
    "Return to the Path to Carcosa": "RtPC",
    "Return to the Forgotten Age": "RtFA",
    "Return to the Circle Undone": "RtCU",
    "Return to the Dream-Eaters": "RtDE",
    "Return to the Innsmouth Conspiracy": "RtIC",
    "Investigator Starter Decks": "Starter",
    "Nathaniel Cho": "Starter",
    "Harvey Walters": "Starter",
    "Winifred Habbamock": "Starter",
    "Jacqueline Fine": "Starter",
    "Stella Clark": "Starter",
    "Promo": "Promo",
    "Books": "Books",
}


def _abbrev_pack(pack_name: str) -> str:
    """Return community abbreviation for a pack name, or the original if unknown."""
    return PACK_ABBREVIATIONS.get(pack_name, pack_name)


async def _check_rate_limit(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if is_admin_user(user_id):
        return True
    allowed, message = rate_limiter.check(user_id, chat_id)
    if not allowed:
        await update.message.reply_text(message)
    return allowed


def _chunks(text: str, size: int = 3900) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]



def _format_uptime(now: datetime) -> str:
    seconds = max(0, int((now - BOT_STARTED_AT).total_seconds()))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _format_list(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "-"
    if value in (None, ""):
        return "-"
    return str(value)


def _format_days(value) -> str:
    names = {
        "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
        "fri": "Fri", "sat": "Sat", "sun": "Sun",
    }
    if not isinstance(value, list):
        return _format_list(value)
    return ", ".join(names.get(str(item), str(item)) for item in value) or "-"


def _time_until_next_post(times: list, days: list, timezone_name: str) -> str:
    """Returns human-readable time until next scheduled post."""
    from zoneinfo import ZoneInfo
    if not times:
        return "not scheduled"
    day_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
    allowed_days = set(day_map[d] for d in (days or []) if d in day_map) or set(range(7))
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = UTC
    now = datetime.now(tz)
    for days_ahead in range(8):
        candidate_date = (now + timedelta(days=days_ahead)).date()
        if candidate_date.weekday() not in allowed_days:
            continue
        for time_str in sorted(times):
            try:
                h, m = map(int, time_str.split(':'))
            except Exception:
                continue
            candidate = datetime(candidate_date.year, candidate_date.month, candidate_date.day, h, m, tzinfo=tz)
            if candidate > now:
                diff = candidate - now
                total_mins = int(diff.total_seconds() / 60)
                hours, mins = divmod(total_mins, 60)
                if days_ahead == 0:
                    return f"today at {time_str} (in {hours}h {mins}m)"
                elif days_ahead == 1:
                    return f"tomorrow at {time_str}"
                else:
                    return f"{candidate_date.strftime('%a')} at {time_str}"
    return "not scheduled"


def _as_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim", "on"}
    return bool(value)


def _safe_status_value(value) -> str:
    return escape(str(value if value not in (None, "") else "-"))


def _code(value) -> str:
    return f"<code>{_safe_status_value(value)}</code>"


def _bold(value) -> str:
    return f"<b>{_safe_status_value(value)}</b>"


_DAY_LABELS = {'mon': 'Seg', 'tue': 'Ter', 'wed': 'Qua', 'thu': 'Qui', 'fri': 'Sex', 'sat': 'Sab', 'sun': 'Dom', 'all': 'Todos'}


def _format_day_config_lines(day_config: dict) -> list[str]:
    if not isinstance(day_config, dict) or not day_config:
        return []
    lines = ["", "<b>Config por dia</b>"]
    order = ['all', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    for code in order:
        cfg = day_config.get(code)
        if not cfg:
            continue
        label = _DAY_LABELS.get(code, code)
        packs = cfg.get('packs') or []
        types = cfg.get('types') or []
        packs_str = f"{len(packs)} packs" if packs else "todos"
        types_str = ", ".join(types[:4]) + ("…" if len(types) > 4 else "") if types else "todos"
        lines.append(f"- {label}: packs={packs_str} | tipos={_code(types_str)}")
    return lines if len(lines) > 2 else []


def _format_status(payload: dict) -> str:
    lines = [
        "<b>Arkham Bot - Online</b>",
        f"Uptime: {payload['uptime']}",
        f"Cartas: {payload['cards_count']}",
    ]
    return "\n".join(lines)


def _format_help_report() -> str:
    lines = [
        "<b>Arkham Bot</b>",
        "",
        "<b>Cartas</b>",
        "- <code>/card</code> - busca guiada por ciclo/pacote",
        "- <code>/sets</code> - navega cartas por set/expansao",
        "- <code>/search &lt;texto&gt;</code> - busca por nome/texto",
        "",
        "<b>Regras e referencias</b>",
        "- <code>/faq &lt;card_code&gt;</code> - FAQ da carta",
        "- <code>/taboo</code> - lista taboo",
        "- <code>/decklist &lt;id&gt;</code> - decklist do ArkhamDB",
        "",
        "<b>Historico</b>",
        "- <code>/cotd</code> - cartas do dia por mes",
        "",
        "<b>Bot</b>",
        "- <code>/status</code> - status operacional",
    ]
    return "\n".join(lines)


def _collect_status_payload(update: Update) -> dict:
    from zoneinfo import ZoneInfo

    from .config import (
        AI_DAILY_CARD_ENABLED,
        AI_MODEL,
        BOT_COMMANDS_POLLING_ENABLED,
        DAILY_POST_DAYS,
        DAILY_POST_ENABLED,
        DAILY_POST_TIMES,
        DAILY_SCHEDULER_STATE_FILE,
        OPENAI_API_KEY,
        SUPABASE_ENABLED,
        TELEGRAM_CHAT_ID,
        TIMEZONE,
    )
    from .local_storage import load_json_file
    from .scheduler import _as_list

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
        from .repositories.settings_repo import get_all_settings

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
            from .supabase_client import get_supabase_client

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
            from .repositories.commands_repo import fetch_pending_commands

            pending_commands = str(len(fetch_pending_commands(50)))
        except Exception as exc:
            logger.warning("status_commands_lookup_failed: %s", exc)
            pending_commands = "erro"

    try:
        local_time = datetime.now(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    state = load_json_file(DAILY_SCHEDULER_STATE_FILE, default={}) or {}
    return {
        "bot": "online",
        "uptime": _format_uptime(now),
        "local_time": local_time,
        "telegram_chat_configured": bool(TELEGRAM_CHAT_ID),
        "telegram_user_id": user_id or "-",
        "daily_post_enabled": _as_bool(daily_post_enabled),
        "daily_post_times": daily_post_times,
        "daily_post_days": daily_post_days,
        "day_config": day_config,
        "last_daily_post_status": state.get("last_daily_post_status", "-"),
        "last_daily_post_card_code": state.get("last_daily_post_card_code", "-"),
        "supabase_configured": SUPABASE_ENABLED,
        "supabase_status": supabase_status,
        "cards_count": cards_count,
        "packs_count": packs_count,
        "taboo_count": taboo_count,
        "next_post": _time_until_next_post(daily_post_times, daily_post_days, timezone_name) if daily_post_enabled else "inactive",
        "ai_daily_card_enabled": bool(AI_DAILY_CARD_ENABLED and OPENAI_API_KEY),
        "ai_model": AI_MODEL if OPENAI_API_KEY else "sem OPENAI_API_KEY",
        "bot_commands_enabled": BOT_COMMANDS_POLLING_ENABLED,
        "is_admin": is_admin,
        "admin_source": admin_source(user_id),
        "pending_commands": pending_commands,
    }


async def bot_started_message(application):
    """Sends a message to the group as soon as the bot starts."""
    if TELEGRAM_CHAT_ID:
        try:
            await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="Bot started and listening for messages...")
        except Exception as e:
            logger.error(f"Could not send startup message. Error: {e}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /status command with operational information."""
    if not await _check_rate_limit(update):
        return
    payload = _collect_status_payload(update)
    await update.message.reply_text(_format_status(payload), parse_mode=ParseMode.HTML)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    await update.message.reply_text(_format_help_report(), parse_mode=ParseMode.HTML)


def _get_pack_positions(pack_code_prefix: str) -> tuple[int, int, int, list[int]]:
    """Returns (count, min_num, max_num, sample_numbers) based on the numeric suffix users type."""
    try:
        client = get_supabase_client()
        if not client:
            return 0, 0, 0, []
        rows = client.get('arkham_cards', {
            'code': f'like.{pack_code_prefix}%',
            'select': 'code',
            'limit': '2000',
        })
        prefix_len = len(pack_code_prefix)
        numbers = sorted(set(
            int(r['code'][prefix_len:])
            for r in rows
            if r.get('code') and r['code'][prefix_len:].isdigit()
        ))
        if not numbers:
            return 0, 0, 0, []
        # Exclude 0 from samples (usually a special/cover card)
        sample_pool = [n for n in numbers if n > 0] or numbers
        k = min(5, len(sample_pool))
        sample = sorted(random.sample(sample_pool, k))
        return len(numbers), numbers[0], numbers[-1], sample
    except Exception as exc:
        logger.warning(f"Failed to get pack positions for {pack_code_prefix}: {exc}")
        return 0, 0, 0, []


async def card_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Sends a message with inline buttons, listing each pack on a separate line
    for better visualization. Includes a Close button.
    """
    if not await _check_rate_limit(update):
        return ConversationHandler.END

    packs = await asyncio.to_thread(_get_cached_pack_list)
    keyboard_layout = []

    for pack in packs:
        label = f"{pack['display_name']} ({pack['card_count']})"
        button = InlineKeyboardButton(label, callback_data=f"SEARCH_{pack['prefix']}")
        keyboard_layout.append([button])

    close_button = InlineKeyboardButton("Close", callback_data=CALLBACK_CANCEL)
    keyboard_layout.append([close_button])

    reply_markup = InlineKeyboardMarkup(keyboard_layout)

    await update.message.reply_text(
        "Choose a pack to search for the card:",
        reply_markup=reply_markup,
        reply_parameters=ReplyParameters(message_id=update.message.message_id),
    )

    return CHOOSING_CARD_NUMBER


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the chosen pack and instructs the user to type the card number."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("SEARCH_"):
        logger.warning(f"Unknown callback_data received: {data!r}")
        await query.edit_message_text("Operation canceled. Type /card to start again.")
        context.user_data.clear()
        return ConversationHandler.END

    pack_code = data.split('_')[1]
    packs = await asyncio.to_thread(_get_cached_pack_list)
    pack_entry = next((p for p in packs if p['prefix'] == pack_code), None)
    if not pack_entry:
        logger.warning(f"Invalid pack callback_data received: {data!r}")
        await query.edit_message_text("Operation canceled. Type /card to start again.")
        context.user_data.clear()
        return ConversationHandler.END

    pack_name = pack_entry['display_name']

    context.user_data['selected_pack_code'] = pack_code

    count, min_pos, max_pos, sample = await asyncio.to_thread(_get_pack_positions, pack_code)

    if count > 0:
        sample_str = ", ".join(str(p) for p in sample)
        card_info = f"({count} cards, {min_pos}–{max_pos})"
        example_hint = f"Ex: {sample_str}"
    else:
        card_info = ""
        example_hint = "Ex: 1, 10, 50"

    await query.edit_message_text(
        text=f"Pack **{pack_name}** {card_info} selected!\n"
             f"👉🏻 Please **now enter the card number** you want to search for ({example_hint}):",
        parse_mode=ParseMode.MARKDOWN
    )

    return CHOOSING_CARD_NUMBER


async def receive_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes the card number, searches the API, and returns the name/image."""
    card_number_input = update.message.text.strip()

    if not card_number_input.isalnum() and not any(c.isdigit() for c in card_number_input):
        await update.message.reply_text("Invalid input. Please enter the card code or number (Ex: 1, 150, L01).")
        return CHOOSING_CARD_NUMBER

    if len(card_number_input) > 5:
        await update.message.reply_text("Invalid input. The card code seems too long. Please enter the card number (Ex: 1, 150, L01).")
        return CHOOSING_CARD_NUMBER

    card_number = card_number_input
    try:
        int(card_number_input)
        card_number = card_number_input.zfill(3)
    except ValueError:
        pass

    pack_code = context.user_data.get('selected_pack_code')

    if not pack_code:
        await update.message.reply_text("⚠️ Pack not selected. Please start again with /card.")
        context.user_data.clear()
        return ConversationHandler.END

    packs = _get_cached_pack_list()
    pack_entry = next((p for p in packs if p['prefix'] == pack_code), None)
    pack_name = pack_entry['display_name'] if pack_entry else f"code {pack_code}"

    full_card_id = f"{pack_code}{card_number}"
    user_msg_id = update.message.message_id
    user_reply = ReplyParameters(message_id=user_msg_id)

    status_msg = await update.message.reply_text(
        f"⏳ Buscando carta **{full_card_id}**...",
        parse_mode=ParseMode.MARKDOWN,
        reply_parameters=user_reply,
    )

    async def _update_status(text: str) -> None:
        try:
            await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    async def _delete_status() -> None:
        try:
            await status_msg.delete()
        except Exception:
            pass

    try:
        card_data, source = await get_card_async(full_card_id)
        if not card_data:
            await _update_status(f"⚠️ Carta `{full_card_id}` não encontrada. Verifique o código e tente novamente.")
            context.user_data.clear()
            return ConversationHandler.END
        logger.info(f"Card {full_card_id} loaded from {source}")
        card_code = card_data.get('code')

        image_src = card_data.get('imagesrc')
        card_image_bytes = None

        for ext in EXTENSIONS_TO_TRY:
            CARD_IMAGE_PATH = image_src if image_src and image_src.lower().endswith(ext) else f"/bundles/cards/{card_code}{ext}"
            card_image_url = urljoin(BASE_URL, CARD_IMAGE_PATH)

            try:
                image_content = await download_image_async(card_image_url)
                card_image_bytes = io.BytesIO(image_content)
                Image.open(card_image_bytes).verify()
                card_image_bytes.seek(0)
                break
            except Exception as img_e:
                logger.warning(f"Failed to download front image for {card_code} ({card_image_url}). Trying next extension: {img_e}")
                continue

        caption = format_card_caption(card_data, is_interactive=True)
        await _delete_status()
        message = None

        if card_image_bytes is None:
            message = await update.message.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_parameters=user_reply,
            )
        else:
            message = await update.message.reply_photo(
                photo=card_image_bytes,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_parameters=user_reply,
            )

        if card_data.get('double_sided') == True and message:
            back_image_src = card_data.get('backimagesrc')
            back_text_raw = card_data.get('back_text')
            back_flavor_raw = card_data.get('back_flavor')

            if back_text_raw or back_flavor_raw:
                back_caption = format_card_back_caption(card_data, back_text_raw, is_interactive=True)
                back_image_bytes = None
                found_back_image = False

                if back_image_src:
                    for ext in EXTENSIONS_TO_TRY:
                        BACK_IMAGE_PATH = back_image_src or f"/bundles/cards/{card_code}b{ext}"
                        BACK_IMAGE_URL = urljoin(BASE_URL, BACK_IMAGE_PATH)

                        try:
                            back_image_content = await download_image_async(BACK_IMAGE_URL)
                            back_image_bytes = io.BytesIO(back_image_content)
                            Image.open(back_image_bytes).verify()
                            back_image_bytes.seek(0)
                            found_back_image = True
                            break
                        except Exception:
                            continue

                if found_back_image:
                    try:
                        await update.message.reply_photo(
                            photo=back_image_bytes,
                            caption=back_caption,
                            parse_mode=ParseMode.HTML,
                            reply_parameters=ReplyParameters(message_id=message.message_id),
                        )
                    except Exception as e:
                        logger.error(f"Failed to post interactive back image: {e}. Trying as text.")
                        found_back_image = False

                if not found_back_image:
                    if "🔗" in back_caption:
                        back_caption = re.sub(r'\n+🔗 <a href=\'[^\']+\'>View on ArkhamDB</a>$', '', back_caption)
                    await update.message.reply_text(
                        text=back_caption,
                        parse_mode=ParseMode.HTML,
                        reply_parameters=ReplyParameters(message_id=message.message_id),
                    )

    except Exception as e:
        logger.error(f"receive_card_number error for {full_card_id}: {e}", exc_info=True)
        await _update_status(f"🚨 Erro ao buscar a carta `{full_card_id}`. Tente novamente mais tarde.")
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allows the user to cancel the conversation at any time with /cancel or button."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.delete_message()
        except Exception:
            await query.edit_message_text("✖️ Fechado.")
    else:
        await update.message.reply_text("Operação cancelada.")

    context.user_data.clear()
    return ConversationHandler.END



async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /faq <card_code>")
        return
    card_code = context.args[0].strip()
    try:
        faq = await _fetch_faq(card_code)
        if not faq:
            await update.message.reply_text(f"Nenhum FAQ encontrado para <code>{escape(card_code)}</code>.", parse_mode=ParseMode.HTML)
            return
        entries = faq if isinstance(faq, list) else [faq]
        lines = [f"📖 <b>FAQ — {escape(card_code)}</b>"]
        for entry in entries:
            if isinstance(entry, dict):
                q = entry.get('question') or entry.get('title') or ''
                a = entry.get('answer') or entry.get('text') or ''
                if q:
                    lines.append(f"\n<b>{escape(str(q))}</b>")
                if a:
                    lines.append(escape(str(a)))
            else:
                lines.append(escape(str(entry)))
        text = "\n".join(lines)
        for chunk in _chunks(text, 3900):
            await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.error(f"faq_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch FAQ right now.")


def _parse_taboo_cards(taboo_list: dict) -> dict:
    """Returns cards_by_code map from a single taboo list entry."""
    import json
    cards = taboo_list.get('cards', [])
    if isinstance(cards, str):
        try:
            cards = json.loads(cards)
        except Exception:
            cards = []
    return {c['code']: c for c in cards if isinstance(c, dict) and c.get('code')}


def _taboo_restriction_label(entry: dict) -> str:
    """Returns a short human-readable restriction for a taboo entry."""
    parts = []
    xp = entry.get('xp')
    if xp is not None:
        parts.append(f"{'+'if xp>0 else ''}{xp} XP")
    dl = entry.get('deck_limit')
    if dl is not None:
        parts.append("Banned" if dl == 0 else f"Limit {dl}/deck")
    if entry.get('exceptional'):
        parts.append("Exceptional")
    if entry.get('text') or entry.get('replacement_text'):
        parts.append("Errata")
    return " · ".join(parts) if parts else "Restrita"


def _taboo_category(entry: dict) -> str:
    dl = entry.get('deck_limit')
    if dl == 0:
        return 'forbidden'
    xp = entry.get('xp')
    if xp is not None:
        return 'xp_up' if xp > 0 else 'xp_down'
    if entry.get('exceptional'):
        return 'exceptional'
    if entry.get('text') or entry.get('replacement_text'):
        return 'errata'
    return 'other'


TABOO_CATEGORIES = {
    'forbidden':   ('', 'Banned'),
    'xp_up':       ('', '+XP (more expensive)'),
    'xp_down':     ('', '−XP (cheaper)'),
    'exceptional': ('', 'Exceptional'),
    'errata':      ('', 'Text errata'),
    'other':       ('', 'Other restrictions'),
}


def _taboo_list_menu_text_and_buttons(taboos: list, name_map: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the taboo list selection message and buttons."""
    sorted_lists = sorted(taboos, key=lambda t: t.get('date_start', ''), reverse=True)
    lines = ["<b>Taboo Lists</b>", "Select a list to explore:\n"]
    buttons = []
    for i, t in enumerate(sorted_lists):
        raw = t.get('date_start', '')[:10]
        date = f"{raw[8:10]}/{raw[5:7]}/{raw[:4]}" if len(raw) == 10 else raw
        tid = t.get('id', i)
        label = f"{'[current] ' if i == 0 else ''}{date}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"TABOO_LIST_{tid}")])
    buttons.append([InlineKeyboardButton("Close", callback_data=CALLBACK_CANCEL)])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def _taboo_detail_text_and_buttons(taboo: dict, cats: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the category summary for a selected taboo list."""
    raw_date = taboo.get('date_start', '')[:10]
    date_str = f"{raw_date[8:10]}/{raw_date[5:7]}/{raw_date[:4]}" if len(raw_date) == 10 else raw_date
    total = sum(len(v) for v in cats.values())
    tid = taboo.get('id', '')
    lines = [f"<b>Taboo — {date_str}</b>", f"{total} card(s) affected\n"]
    for cat_key, (icon, label) in TABOO_CATEGORIES.items():
        count = len(cats.get(cat_key, []))
        if count:
            lines.append(f"{label}: <b>{count}</b>")
    buttons = []
    for cat_key, (icon, label) in TABOO_CATEGORIES.items():
        count = len(cats.get(cat_key, []))
        if count:
            buttons.append([InlineKeyboardButton(f"{label} ({count})", callback_data=f"TABOO_CAT_{cat_key}_0")])
    buttons.append([
        InlineKeyboardButton("Lists", callback_data="TABOO_LISTS"),
        InlineKeyboardButton("Close", callback_data=CALLBACK_CANCEL),
    ])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def taboo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    try:
        taboos, all_cards_raw = await asyncio.gather(
            _fetch_all_taboos(),
            _fetch_all_cards(include_encounter=True),
        )
        if not taboos:
            await update.message.reply_text("No taboo lists found.")
            return

        name_map = {c['code']: {'name': c.get('name') or c.get('real_name') or c['code'], 'pack': c.get('pack_name') or ''} for c in all_cards_raw if c.get('code')}
        sorted_lists = sorted(taboos, key=lambda t: t.get('date_start', ''), reverse=True)
        context.bot_data['taboo_all_lists'] = sorted_lists
        context.bot_data['taboo_name_map'] = name_map

        # If searching a specific card — search on most recent list
        if context.args:
            q = " ".join(context.args).strip().lower()
            by_code = _parse_taboo_cards(sorted_lists[0])
            matches = {code: entry for code, entry in by_code.items()
                       if q in _taboo_name(name_map, code).lower() or q == code.lower()}
            if not matches:
                await update.message.reply_text(f"No taboo restriction found for «{escape(q)}».", parse_mode=ParseMode.HTML)
                return
            if len(matches) == 1:
                code, entry = next(iter(matches.items()))
                await _send_taboo_card(update, code, entry, name_map)
                return
            lines = [f"<b>Resultados taboo para «{escape(q)}»:</b>"]
            for code, entry in list(matches.items())[:20]:
                lines.append(f"• <b>{escape(_taboo_name(name_map, code))}</b> ({code}) — {escape(_taboo_restriction_label(entry))}")
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
            return

        text, markup = _taboo_list_menu_text_and_buttons(sorted_lists, name_map)
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
            reply_parameters=ReplyParameters(message_id=update.message.message_id),
        )

    except Exception as exc:
        logger.error(f"taboo_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not load the taboo list right now.")


async def taboo_list_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User selected a specific taboo list — show its categories."""
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("TABOO_LIST_", "")
    all_lists = context.bot_data.get('taboo_all_lists', [])
    name_map = context.bot_data.get('taboo_name_map', {})
    taboo = next((t for t in all_lists if str(t.get('id', '')) == tid), None)
    if not taboo:
        await query.answer("List not found.", show_alert=True)
        return
    by_code = _parse_taboo_cards(taboo)
    cats: dict[str, list] = {k: [] for k in TABOO_CATEGORIES}
    for code, entry in by_code.items():
        cat = _taboo_category(entry)
        cats.setdefault(cat, []).append((code, entry))
    context.bot_data['taboo_selected'] = taboo
    context.bot_data['taboo_by_code'] = by_code
    context.bot_data['taboo_cats'] = cats
    text, markup = _taboo_detail_text_and_buttons(taboo, cats)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def taboo_lists_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Back to the list selection screen."""
    query = update.callback_query
    await query.answer()
    all_lists = context.bot_data.get('taboo_all_lists', [])
    name_map = context.bot_data.get('taboo_name_map', {})
    if not all_lists:
        await query.answer("Session expired. Use /taboo again.", show_alert=True)
        return
    text, markup = _taboo_list_menu_text_and_buttons(all_lists, name_map)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


def _taboo_name(name_map: dict, code: str) -> str:
    v = name_map.get(code, {})
    return v.get('name', code) if isinstance(v, dict) else str(v)


async def _send_taboo_card(update: Update, code: str, entry: dict, name_map: dict) -> None:
    """Sends a card image with its taboo restriction info."""
    card, _ = await get_card_async(code)
    name = _taboo_name(name_map, code) or (card.get('name') if card else code)
    restriction = _taboo_restriction_label(entry)
    text_note = entry.get('text') or entry.get('replacement_text') or ''

    if card:
        caption, is_spoiler = _spoiler_caption(card)
        taboo_block = f"\n\n<b>Taboo:</b> {escape(restriction)}"
        if text_note:
            taboo_block += f"\n<i>{escape(text_note)}</i>"
        caption = caption + taboo_block
        image_src = card.get('imagesrc') or card.get('image_src')
        img = await _fetch_card_image(code, image_src)
        target = update.message or (update.callback_query.message if update.callback_query else None)
        if target:
            if img:
                await target.reply_photo(photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler)
            else:
                await target.reply_text(caption, parse_mode=ParseMode.HTML)
    else:
        text = f"<b>{escape(name)}</b> (<code>{code}</code>)\n<b>Taboo:</b> {escape(restriction)}"
        if text_note:
            text += f"\n<i>{escape(text_note)}</i>"
        target = update.message or (update.callback_query.message if update.callback_query else None)
        if target:
            await target.reply_text(text, parse_mode=ParseMode.HTML)


async def taboo_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.replace("TABOO_CAT_", "").rsplit("_", 1)
    cat_key = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0

    cats = context.bot_data.get('taboo_cats', {})
    name_map = context.bot_data.get('taboo_name_map', {})
    entries = cats.get(cat_key, [])
    icon, label = TABOO_CATEGORIES.get(cat_key, ('', cat_key))

    PAGE = 10
    total = len(entries)
    total_pages = max(1, (total + PAGE - 1) // PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = entries[page * PAGE:(page + 1) * PAGE]

    buttons = []
    for code, entry in chunk:
        name = _taboo_name(name_map, code)
        restriction = _taboo_restriction_label(entry)
        btn_label = f"{code} · {name} · {restriction}"
        if len(btn_label) > 64:
            btn_label = btn_label[:61] + "…"
        buttons.append([InlineKeyboardButton(btn_label, callback_data=f"TABOO_CARD_{code}")])

    has_prev = page > 0
    has_next = page < total_pages - 1
    btn_prev = InlineKeyboardButton("Previous", callback_data=f"TABOO_CAT_{cat_key}_{page-1}")
    btn_next = InlineKeyboardButton("Next", callback_data=f"TABOO_CAT_{cat_key}_{page+1}")
    btn_back = InlineKeyboardButton("Back", callback_data="TABOO_BACK")
    btn_close = InlineKeyboardButton("Close", callback_data=CALLBACK_CANCEL)
    if has_prev and has_next:
        buttons.append([btn_prev, btn_close, btn_next])
    elif has_prev:
        buttons.append([btn_prev, btn_back, btn_close])
    elif has_next:
        buttons.append([btn_close, btn_next])
    else:
        buttons.append([btn_back, btn_close])

    text = f"<b>{label}</b> — {total} card(s) — page {page+1}/{total_pages}:"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def taboo_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    code = query.data.replace("TABOO_CARD_", "")
    by_code = context.bot_data.get('taboo_by_code', {})
    name_map = context.bot_data.get('taboo_name_map', {})
    entry = by_code.get(code)
    if not entry:
        await query.answer("Card not found in taboo list.", show_alert=True)
        return

    card, _ = await get_card_async(code)
    name = _taboo_name(name_map, code) or (card.get('name') if card else code)
    restriction = _taboo_restriction_label(entry)
    text_note = entry.get('text') or entry.get('replacement_text') or ''

    lines = [f"<b>{escape(name)}</b> (<code>{code}</code>)"]
    if card:
        pack = card.get('pack_name', '')
        position = card.get('position', '')
        if pack:
            lines.append(f"Pack: {escape(pack)}{f' #{position}' if position else ''}")
    lines.append(f"\n<b>Taboo:</b> {escape(restriction)}")
    if text_note:
        lines.append(f"<i>{escape(text_note)}</i>")

    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="TABOO_BACK")]])
    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=markup)


async def taboo_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Back to the selected taboo list's category screen."""
    query = update.callback_query
    await query.answer()
    taboo = context.bot_data.get('taboo_selected', {})
    cats = context.bot_data.get('taboo_cats', {})
    if not taboo:
        await query.answer("Session expired. Use /taboo again.", show_alert=True)
        return
    text, markup = _taboo_detail_text_and_buttons(taboo, cats)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def decklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /decklist <decklist_id>")
        return
    from .arkhamdb_client import fetch_decklist_sync

    raw_arg = context.args[0].strip()
    match = re.search(r"(\d+)", raw_arg)
    if not match:
        await update.message.reply_text("Invalid decklist id.")
        return
    decklist_id = match.group(1)
    try:
        deck = await asyncio.to_thread(fetch_decklist_sync, decklist_id)
        name = deck.get('name', 'Untitled decklist')
        investigator = deck.get('investigator_name') or deck.get('investigator_code') or 'Unknown investigator'
        slots = deck.get('slots') if isinstance(deck.get('slots'), dict) else {}
        await update.message.reply_text(
            f"Decklist: {name}\nInvestigator: {investigator}\nCards in slots: {len(slots)}\nhttps://arkhamdb.com/decklist/view/{decklist_id}"
        )
    except Exception as exc:
        logger.error(f"decklist_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch decklist right now.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_rate_limit(update):
        return ConversationHandler.END
    # If query was passed inline (e.g. /search shrivelling), run immediately
    if context.args:
        context.user_data["search_user_msg_id"] = update.message.message_id
        return await _search_run(update, context, " ".join(context.args).strip())
    prompt = await update.message.reply_text(
        "🔍 Digite o nome ou código da carta:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancelar", callback_data=CALLBACK_CANCEL)
        ]])
    )
    context.user_data["search_prompt_msg_id"] = prompt.message_id
    context.user_data["search_prompt_chat_id"] = prompt.chat_id
    context.user_data["search_prompt_obj"] = prompt
    return SEARCH_WAITING_QUERY


async def search_receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_rate_limit(update):
        return ConversationHandler.END
    query = (update.message.text or "").strip()
    if not query:
        await update.message.reply_text("Digite algo para buscar.")
        return SEARCH_WAITING_QUERY
    # Delete the original prompt and send a "Pesquisando…" message in its place
    old_prompt = context.user_data.pop("search_prompt_obj", None)
    context.user_data.pop("search_prompt_msg_id", None)
    context.user_data.pop("search_prompt_chat_id", None)
    if old_prompt:
        try:
            await old_prompt.delete()
        except Exception:
            pass
    context.user_data["search_user_msg_id"] = update.message.message_id
    searching_msg = await update.message.reply_text("🔍 Pesquisando…")
    context.user_data["search_prompt_obj"] = searching_msg
    return await _search_run(update, context, query)


async def _fetch_card_image(card_code: str, image_src: str | None = None) -> io.BytesIO | None:
    """Tries all extensions and returns a valid image BytesIO or None."""
    import httpx
    urls = []
    if image_src:
        urls.append(urljoin(BASE_URL, image_src))
    for ext in EXTENSIONS_TO_TRY:
        url = urljoin(BASE_URL, f"/bundles/cards/{card_code}{ext}")
        if url not in urls:
            urls.append(url)
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                continue
            raw = resp.content
            # Validate it's a real image by opening (don't call verify — it corrupts the buffer)
            buf = io.BytesIO(raw)
            img = Image.open(buf)
            img.load()
            buf.seek(0)
            return buf
        except Exception:
            continue
    return None


def _spoiler_caption(card: dict) -> tuple[str, bool]:
    """Returns (caption, is_spoiler). If spoiler, wraps body in <tg-spoiler>."""
    is_spoiler = bool(card.get('spoiler'))
    full_caption = format_card_caption(card, is_interactive=True)
    if not is_spoiler:
        return full_caption, False
    name = escape(card.get('name') or card.get('real_name') or card.get('code', ''))
    # Keep name visible, wrap everything else in spoiler tag
    lines = full_caption.split('\n', 1)
    body = lines[1] if len(lines) > 1 else ''
    caption = f"{lines[0]}\n<tg-spoiler>{body}</tg-spoiler>" if body else lines[0]
    return caption, True


async def _send_card_by_code(update: Update, code: str, prompt_message=None) -> None:
    """Fetches and sends a card (front + back if double-sided) as reply to user's message.
    prompt_message: the bot's 'Pesquisando…' message — deleted after card is sent."""
    card, _ = await get_card_async(code)
    target = update.message or (update.callback_query.message if update.callback_query else None)

    if not card:
        if prompt_message:
            try:
                await prompt_message.delete()
            except Exception:
                pass
        if target:
            reply_to = update.message.message_id if update.message else None
            await target.reply_text(
                f"Carta <code>{escape(code)}</code> não encontrada.",
                parse_mode=ParseMode.HTML,
                **({"reply_parameters": ReplyParameters(message_id=reply_to)} if reply_to else {})
            )
        return

    caption, is_spoiler = _spoiler_caption(card)
    image_src = card.get('imagesrc') or card.get('image_src')
    img = await _fetch_card_image(code, image_src)

    if not target:
        return

    if prompt_message:
        try:
            await prompt_message.delete()
        except Exception:
            pass

    user_msg = update.message

    if is_spoiler:
        await user_msg.reply_text("⚠️ <b>Atenção: esta carta contém spoiler!</b>", parse_mode=ParseMode.HTML, do_quote=True)

    if img:
        front_msg = await user_msg.reply_photo(photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, do_quote=True)
    else:
        front_msg = await user_msg.reply_text(caption, parse_mode=ParseMode.HTML, do_quote=True)

    # Post back side if double-sided
    if card.get('double_sided') and front_msg:
        back_image_src = card.get('backimagesrc')
        back_text_raw = card.get('back_text')
        back_flavor_raw = card.get('back_flavor')
        if back_text_raw or back_flavor_raw:
            back_caption = format_card_back_caption(card, back_text_raw, is_interactive=True)
            if is_spoiler:
                lines = back_caption.split('\n', 1)
                back_caption = f"{lines[0]}\n<tg-spoiler>{lines[1]}</tg-spoiler>" if len(lines) > 1 else lines[0]
            back_img = await _fetch_card_image(f"{code}b", back_image_src)
            back_rp = ReplyParameters(message_id=front_msg.message_id)
            if back_img:
                try:
                    await front_msg.reply_photo(photo=back_img, caption=back_caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, do_quote=True)
                except Exception:
                    await front_msg.reply_text(back_caption, parse_mode=ParseMode.HTML, do_quote=True)
            else:
                await front_msg.reply_text(back_caption, parse_mode=ParseMode.HTML, do_quote=True)


async def search_card_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    card_code = query.data.replace("CARD_SELECT_", "")
    user_msg_id = context.user_data.get("search_user_msg_id")
    try:
        card, _ = await get_card_async(card_code)
        if not card:
            await query.edit_message_text("Carta não encontrada.")
            return ConversationHandler.END
        caption, is_spoiler = _spoiler_caption(card)
        image_src = card.get('imagesrc') or card.get('image_src')
        img = await _fetch_card_image(card_code, image_src)
        try:
            await query.delete_message()
        except Exception:
            pass
        _pop_search_prompt(context)
        bot = query.message.get_bot()
        chat_id = query.message.chat_id
        rp = ReplyParameters(message_id=user_msg_id) if user_msg_id else None
        if is_spoiler:
            await bot.send_message(chat_id=chat_id, text="⚠️ <b>Atenção: esta carta contém spoiler!</b>", parse_mode=ParseMode.HTML, reply_parameters=rp)
        if img:
            front_msg = await bot.send_photo(chat_id=chat_id, photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, reply_parameters=rp)
        else:
            front_msg = await bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.HTML, reply_parameters=rp)
        # Post back side if double-sided
        if card.get('double_sided') and front_msg:
            back_text_raw = card.get('back_text')
            back_flavor_raw = card.get('back_flavor')
            if back_text_raw or back_flavor_raw:
                back_caption = format_card_back_caption(card, back_text_raw, is_interactive=True)
                if is_spoiler:
                    lines = back_caption.split('\n', 1)
                    back_caption = f"{lines[0]}\n<tg-spoiler>{lines[1]}</tg-spoiler>" if len(lines) > 1 else lines[0]
                back_img = await _fetch_card_image(f"{card_code}b", card.get('backimagesrc'))
                back_rp = ReplyParameters(message_id=front_msg.message_id)
                if back_img:
                    try:
                        await bot.send_photo(chat_id=chat_id, photo=back_img, caption=back_caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, reply_parameters=back_rp)
                    except Exception:
                        await bot.send_message(chat_id=chat_id, text=back_caption, parse_mode=ParseMode.HTML, reply_parameters=back_rp)
                else:
                    await bot.send_message(chat_id=chat_id, text=back_caption, parse_mode=ParseMode.HTML, reply_parameters=back_rp)
    except Exception as exc:
        logger.error(f"search_card_selected error: {exc}", exc_info=True)
        try:
            await query.edit_message_text("Erro ao carregar a carta.")
        except Exception:
            pass
    return ConversationHandler.END


PAGE_SIZE = 10


def _search_page(results: list, page: int, query: str) -> tuple[InlineKeyboardMarkup, str]:
    total = len(results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = results[start:start + PAGE_SIZE]

    buttons = []
    for c in chunk:
        code = c.get('code', '')
        name = c.get('name') or c.get('real_name') or code
        pack = _abbrev_pack(c.get('pack_name') or '')
        spoiler_flag = "⚠️ " if c.get('spoiler') else ""
        label = f"{spoiler_flag}{pack} — {name} — {code}"
        if len(label) > 64:
            label = label[:61] + "…"
        buttons.append([InlineKeyboardButton(label, callback_data=f"CARD_SELECT_{code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"SEARCH_PAGE_{page - 1}"))
    nav.append(InlineKeyboardButton("❌ Cancelar", callback_data=CALLBACK_CANCEL))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Próximo", callback_data=f"SEARCH_PAGE_{page + 1}"))
    buttons.append(nav)

    text = f"🔍 <b>{total} resultado(s)</b> para «{escape(query)}» — página {page + 1}/{total_pages}:"
    return InlineKeyboardMarkup(buttons), text


async def search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("SEARCH_PAGE_", ""))
    user_id = update.effective_user.id
    results = context.bot_data.get(f"search_{user_id}")
    if not results:
        await query.edit_message_text("Sessão expirada. Use /search novamente.")
        return
    # Recover original query from current message text
    msg_text = query.message.text or ""
    raw_query = ""
    if "«" in msg_text and "»" in msg_text:
        raw_query = msg_text.split("«")[1].split("»")[0]
    markup, text = _search_page(results, page=page, query=raw_query)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


def _pop_search_prompt(context: ContextTypes.DEFAULT_TYPE):
    """Returns the stored prompt message object and clears search prompt keys.
    Does NOT clear search_user_msg_id — that is kept until the card is sent."""
    prompt = context.user_data.pop("search_prompt_obj", None)
    context.user_data.pop("search_prompt_msg_id", None)
    context.user_data.pop("search_prompt_chat_id", None)
    context.user_data.pop("search_user_chat_id", None)
    return prompt


async def _search_run(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> int:
    from .repositories.cards_repo import search_cards

    q = query.strip()
    is_numeric = re.fullmatch(r'\d+', q) is not None
    is_card_code = re.fullmatch(r'\d{4,6}[a-z]?', q) is not None

    try:
        # Exact card code (e.g. 01001 or 09519a) → show directly without searching
        if is_card_code:
            prompt = _pop_search_prompt(context)
            await _send_card_by_code(update, q, prompt_message=prompt)
            return ConversationHandler.END

        # DB search (falls back to in-memory on DB failure)
        try:
            results = await asyncio.to_thread(
                search_cards, q, True, is_numeric or is_card_code
            )
        except Exception as exc:
            logger.warning(f"DB search_cards failed, falling back to all-cards: {exc}")
            cards = await _fetch_all_cards(include_encounter=True)
            q_lower = q.lower()
            if is_numeric or is_card_code:
                results = [c for c in cards if (c.get('code') or '').startswith(q)]
            else:
                results = [
                    c for c in cards
                    if q_lower in (c.get('name') or '').lower()
                    or q_lower in (c.get('real_name') or '').lower()
                ]

        # Exact single-code match → show directly
        if len(results) == 1 or (results and results[0].get('code') == q):
            exact = next((c for c in results if (c.get('code') or '') == q), None)
            if exact or len(results) == 1:
                code = (exact or results[0]).get('code', q)
                prompt = _pop_search_prompt(context)
                await _send_card_by_code(update, code, prompt_message=prompt)
                return ConversationHandler.END

        # For multi-result and no-result paths, delete the "Pesquisando…" message first
        searching_msg = _pop_search_prompt(context)
        async def _delete_searching():
            if searching_msg:
                try:
                    await searching_msg.delete()
                except Exception:
                    pass
        await _delete_searching()

        if not results:
            msg = "Nenhuma carta encontrada. Tente outro termo."
            if update.message:
                await update.message.reply_text(msg)
            elif update.callback_query:
                await update.callback_query.edit_message_text(msg)
            return ConversationHandler.END

        # Store full result list for pagination
        all_results = results
        user_id = update.effective_user.id
        context.bot_data[f"search_{user_id}"] = all_results
        markup, text = _search_page(all_results, page=0, query=q)
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    except Exception as exc:
        logger.error(f"search_run error: {exc}", exc_info=True)
        _pop_search_prompt(context)
        if update.message:
            await update.message.reply_text("Erro ao buscar cartas.")
    return ConversationHandler.END


async def sets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all available packs as inline buttons. Clicking one lists its cards."""
    if not await _check_rate_limit(update):
        return
    try:
        cards = await _fetch_all_cards()
        # Build unique pack list preserving order
        seen: dict[str, str] = {}
        for c in cards:
            code = c.get('pack_code') or ''
            name = c.get('pack_name') or code
            if code and code not in seen:
                seen[code] = name
        if not seen:
            await update.message.reply_text("Nenhum set disponível.")
            return
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"SET_BROWSE_{code}")]
            for code, name in seen.items()
        ]
        await update.message.reply_text(
            "📦 Escolha um set para ver as cartas:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as exc:
        logger.error(f"sets_command error: {exc}", exc_info=True)
        await update.message.reply_text("Erro ao carregar sets.")


async def set_browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows cards of the selected pack as inline buttons."""
    query = update.callback_query
    await query.answer()
    pack_code = query.data.replace("SET_BROWSE_", "")
    try:
        cards = await _fetch_all_cards()
        pack_cards = [c for c in cards if c.get('pack_code') == pack_code]
        if not pack_cards:
            await query.edit_message_text("Nenhuma carta encontrada neste set.")
            return
        pack_name = pack_cards[0].get('pack_name') or pack_code
        buttons = []
        for c in pack_cards:
            code = c.get('code', '')
            name = c.get('name') or c.get('real_name') or code
            position = c.get('position', '')
            label = f"{position:>3}. {name}" if position else name
            if len(label) > 64:
                label = label[:61] + "…"
            buttons.append([InlineKeyboardButton(label, callback_data=f"CARD_SELECT_{code}")])
        buttons.append([InlineKeyboardButton("« Voltar aos sets", callback_data="SETS_BACK")])
        await query.edit_message_text(
            f"📦 <b>{escape(pack_name)}</b> — {len(pack_cards)} carta(s):",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as exc:
        logger.error(f"set_browse_callback error: {exc}", exc_info=True)
        await query.edit_message_text("Erro ao carregar cartas do set.")


async def sets_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns to the pack list."""
    query = update.callback_query
    await query.answer()
    try:
        cards = await _fetch_all_cards()
        seen: dict[str, str] = {}
        for c in cards:
            code = c.get('pack_code') or ''
            name = c.get('pack_name') or code
            if code and code not in seen:
                seen[code] = name
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"SET_BROWSE_{code}")]
            for code, name in seen.items()
        ]
        await query.edit_message_text(
            "📦 Escolha um set para ver as cartas:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as exc:
        logger.error(f"sets_back_callback error: {exc}", exc_info=True)
        await query.edit_message_text("Erro ao carregar sets.")








MONTHS_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _cotd_fetch_years() -> list[int]:
    from .supabase_client import get_supabase_client
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get('bot_posting_history', {
        'select': 'created_at',
        'source': 'eq.scheduled',
        'order': 'created_at.asc',
    })
    years = sorted({datetime.fromisoformat(r['created_at']).year for r in rows if r.get('created_at')})
    return years


def _cotd_fetch_months(year: int) -> list[int]:
    from .supabase_client import get_supabase_client
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get('bot_posting_history', [
        ('select', 'created_at'),
        ('source', 'eq.scheduled'),
        ('created_at', f'gte.{year}-01-01T00:00:00Z'),
        ('created_at', f'lt.{year + 1}-01-01T00:00:00Z'),
        ('order', 'created_at.asc'),
    ])
    months = sorted({datetime.fromisoformat(r['created_at']).month for r in rows if r.get('created_at')})
    return months


def _cotd_fetch_cards(year: int, month: int, tz_name: str = 'America/Sao_Paulo') -> list[dict]:
    from zoneinfo import ZoneInfo
    from .supabase_client import get_supabase_client
    client = get_supabase_client()
    if not client:
        return []
    start = f'{year}-{month:02d}-01T00:00:00Z'
    end_month = month + 1 if month < 12 else 1
    end_year = year if month < 12 else year + 1
    end = f'{end_year}-{end_month:02d}-01T00:00:00Z'
    rows = client.get('bot_posting_history', [
        ('select', 'card_code,card_name,created_at'),
        ('source', 'eq.scheduled'),
        ('created_at', f'gte.{start}'),
        ('created_at', f'lt.{end}'),
        ('order', 'created_at.asc'),
    ])
    tz = ZoneInfo(tz_name)
    result = []
    for r in rows:
        if not r.get('created_at'):
            continue
        dt = datetime.fromisoformat(r['created_at']).astimezone(tz)
        result.append({'code': r['card_code'], 'name': r['card_name'], 'day': dt.day})
    return result


async def cotd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_rate_limit(update):
        return
    years = await asyncio.to_thread(_cotd_fetch_years)
    if not years:
        await update.message.reply_text("Nenhuma carta do dia encontrada.")
        return
    buttons = [[InlineKeyboardButton(str(y), callback_data=f"COTD_YEAR_{y}")] for y in years]
    await update.message.reply_text("Selecione o ano:", reply_markup=InlineKeyboardMarkup(buttons))


async def cotd_year_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    year = int(query.data.split('_')[-1])
    months = await asyncio.to_thread(_cotd_fetch_months, year)
    if not months:
        await query.edit_message_text("Nenhuma carta encontrada para este ano.")
        return
    rows = [months[i:i+4] for i in range(0, len(months), 4)]
    buttons = [
        [InlineKeyboardButton(MONTHS_PT[m - 1], callback_data=f"COTD_MONTH_{year}_{m}") for m in row]
        for row in rows
    ]
    buttons.append([InlineKeyboardButton("« Voltar", callback_data="COTD_BACK")])
    await query.edit_message_text(f"Selecione o mês ({year}):", reply_markup=InlineKeyboardMarkup(buttons))


async def cotd_month_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, _, year_str, month_str = query.data.split('_')
    year, month = int(year_str), int(month_str)
    cards = await asyncio.to_thread(_cotd_fetch_cards, year, month)
    if not cards:
        await query.edit_message_text("Nenhuma carta encontrada para este mês.")
        return
    month_name = MONTHS_PT[month - 1]
    lines = [f"<b>Cartas do dia - {month_name}/{year}</b>", ""]
    for c in cards:
        name = escape(c['name'] or c['code'])
        url = f"https://arkhamdb.com/card/{c['code']}"
        lines.append(f"{c['day']:02d}/{month:02d} - <a href='{url}'>{name}</a>")
    text = "\n".join(lines)
    back = InlineKeyboardMarkup([[InlineKeyboardButton("« Voltar", callback_data=f"COTD_YEAR_{year}")]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back)


async def cotd_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    years = await asyncio.to_thread(_cotd_fetch_years)
    buttons = [[InlineKeyboardButton(str(y), callback_data=f"COTD_YEAR_{y}")] for y in years]
    await query.edit_message_text("Selecione o ano:", reply_markup=InlineKeyboardMarkup(buttons))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs unhandled Telegram handler errors without exposing details to users."""
    logger.exception("Unhandled Telegram handler error", exc_info=context.error)


def register_handlers(application):
    """Registers Telegram command and callback handlers."""
    card_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("card", card_command)],
        states={
            CHOOSING_CARD_NUMBER: [
                CallbackQueryHandler(button_callback, pattern='^SEARCH_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_card_number)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start_command),
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"),
        ]
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("taboo", taboo_command))
    application.add_handler(CallbackQueryHandler(taboo_list_select_callback, pattern=r'^TABOO_LIST_'))
    application.add_handler(CallbackQueryHandler(taboo_lists_back_callback, pattern=r'^TABOO_LISTS$'))
    application.add_handler(CallbackQueryHandler(taboo_category_callback, pattern=r'^TABOO_CAT_'))
    application.add_handler(CallbackQueryHandler(taboo_card_callback, pattern=r'^TABOO_CARD_'))
    application.add_handler(CallbackQueryHandler(taboo_back_callback, pattern=r'^TABOO_BACK$'))
    application.add_handler(CommandHandler("decklist", decklist_command))
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            SEARCH_WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_receive_query),
                CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start_command),
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"),
        ],
    )
    application.add_handler(search_conv_handler)
    application.add_handler(CallbackQueryHandler(search_card_selected, pattern=r'^CARD_SELECT_'))
    application.add_handler(CallbackQueryHandler(search_page_callback, pattern=r'^SEARCH_PAGE_\d+$'))
    application.add_handler(CommandHandler("sets", sets_command))
    application.add_handler(CallbackQueryHandler(set_browse_callback, pattern=r'^SET_BROWSE_'))
    application.add_handler(CallbackQueryHandler(sets_back_callback, pattern=r'^SETS_BACK$'))
    application.add_handler(CommandHandler("cotd", cotd_command))
    application.add_handler(CallbackQueryHandler(cotd_year_callback, pattern=r'^COTD_YEAR_\d+$'))
    application.add_handler(CallbackQueryHandler(cotd_month_callback, pattern=r'^COTD_MONTH_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(cotd_back_callback, pattern=r'^COTD_BACK$'))
    application.add_handler(card_conv_handler)
    application.add_handler(CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^NOOP$"))
    application.add_error_handler(error_handler)
