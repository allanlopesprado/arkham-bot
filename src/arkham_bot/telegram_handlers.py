import io
import logging
import re
from datetime import UTC, datetime
from html import escape
from urllib.parse import urljoin

from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .arkhamdb_client import download_image_async
from .card_provider import get_card_async
from .config import (
    BASE_URL,
    CALLBACK_CANCEL,
    CHOOSING_CARD_NUMBER,
    SEARCH_WAITING_QUERY,
    EXTENSIONS_TO_TRY,
    PACK_CODES,
    TELEGRAM_CHAT_ID,
)
from .permissions import admin_source, is_admin_user
from .rate_limit import rate_limiter
from .text_formatters import format_card_back_caption, format_card_caption


logger = logging.getLogger(__name__)
BOT_STARTED_AT = datetime.now(UTC)


async def _check_rate_limit(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if is_admin_user(user_id):
        return True
    allowed, message = rate_limiter.check(user_id, chat_id)
    if not allowed:
        await update.message.reply_text(message)
    return allowed


async def _require_admin(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if is_admin_user(user_id):
        return True
    await update.message.reply_text("Administrative command restricted.")
    return False


def _card_line(card: dict) -> str:
    return f"{card.get('code')} — {card.get('name') or card.get('real_name') or 'Unnamed'}"


def _chunks(text: str, size: int = 3900) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def _send_long_or_private(update: Update, text: str, *, private_threshold: int = 1800) -> None:
    if len(text) <= private_threshold:
        for chunk in _chunks(text):
            await update.message.reply_text(chunk)
        return
    try:
        for chunk in _chunks(text):
            await update.effective_user.send_message(chunk)
        await update.message.reply_text("Enviei os detalhes no privado.")
    except Exception:
        await update.message.reply_text("Não consegui enviar no privado. Envie /start para o bot no privado e tente novamente.")


def _yes_no(value: bool) -> str:
    return "sim" if value else "nao"


def _active_inactive(value: bool) -> str:
    return "ativo" if value else "inativo"


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
        "mon": "seg",
        "tue": "ter",
        "wed": "qua",
        "thu": "qui",
        "fri": "sex",
        "sat": "sab",
        "sun": "dom",
    }
    if not isinstance(value, list):
        return _format_list(value)
    return ", ".join(names.get(str(item), str(item)) for item in value) or "-"


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


def _format_status_report(payload: dict) -> str:
    lines = [
        "<b>Arkham Bot</b>",
        "<code>Status operacional</code>",
        "",
        "<b>Resumo</b>",
        f"- Bot: {_bold(payload['bot'])}",
        f"- Uptime: {_code(payload['uptime'])}",
        f"- Horario local: {_code(payload['local_time'])}",
        "",
        "<b>Telegram</b>",
        f"- Chat configurado: {_bold(_yes_no(payload['telegram_chat_configured']))}",
        f"- Usuario: {_code(payload['telegram_user_id'])}",
        "",
        "<b>Agendamento</b>",
        f"- Postagem diaria: {_bold(_active_inactive(payload['daily_post_enabled']))}",
        f"- Horarios: {_code(_format_list(payload['daily_post_times']))}",
        f"- Dias: {_code(_format_days(payload['daily_post_days']))}",
        f"- Ultimo resultado: {_code(payload['last_daily_post_status'])}",
        *_format_day_config_lines(payload.get('day_config', {})),
        f"- Ultima carta: {_code(payload['last_daily_post_card_code'])}",
        "",
        "<b>Dados</b>",
        f"- Supabase: {_bold(payload['supabase_status'])}",
        f"- Cartas: {_code(payload['cards_count'])}",
        f"- Packs: {_code(payload['packs_count'])}",
        f"- IA diaria: {_bold(_active_inactive(payload['ai_daily_card_enabled']))}",
        f"- Modelo IA: {_code(payload['ai_model'])}",
        f"- Worker de comandos: {_bold(_active_inactive(payload['bot_commands_enabled']))}",
        "",
        "<b>Admin</b>",
    ]
    if payload["is_admin"]:
        lines.extend([
            f"- Acesso: {_code(payload['admin_source'])}",
            f"- Fila pendente/retry: {_code(payload['pending_commands'])}",
        ])
    else:
        lines.append("- Acesso: nao")
    return "\n".join(lines)


def _format_help_report(is_admin: bool) -> str:
    lines = [
        "<b>Arkham Bot</b>",
        "<code>Comandos disponiveis</code>",
        "",
        "<b>Cartas</b>",
        "- <code>/card</code> - busca guiada por ciclo/pacote",
        "- <code>/random</code> - carta aleatoria",
        "- <code>/today</code> - ultima carta diaria registrada",
        "- <code>/search &lt;texto&gt;</code> - busca por nome/texto",
        "- <code>/pack &lt;codigo&gt;</code> - cartas de um pacote",
        "- <code>/faction &lt;codigo&gt;</code> - cartas por faccao",
        "- <code>/type &lt;codigo&gt;</code> - cartas por tipo",
        "- <code>/xp &lt;numero&gt;</code> - cartas por XP",
        "",
        "<b>Regras e referencias</b>",
        "- <code>/faq &lt;card_code&gt;</code> - FAQ da carta",
        "- <code>/taboo</code> - lista taboo",
        "- <code>/decklist &lt;id&gt;</code> - decklist do ArkhamDB",
        "",
        "<b>Bot</b>",
        "- <code>/status</code> - status operacional",
        "- <code>/menu</code> - mostra este menu",
        "- <code>/cancel</code> - cancela uma busca em andamento",
    ]
    if is_admin:
        lines.extend([
            "",
            "<b>Admin</b>",
            "- <code>/admin</code> - valida permissao",
            "- <code>/post &lt;card_code&gt;</code> - posta carta agora",
            "- <code>/repost &lt;card_code&gt;</code> - reposta carta",
            "- <code>/skip &lt;card_code&gt;</code> - marca carta como usada",
            "- <code>/pause</code> - pausa postagem diaria",
            "- <code>/resume</code> - retoma postagem diaria",
            "- <code>/settings</code> - mostra settings do Supabase",
            "- <code>/queue</code> - mostra comandos pendentes",
            "- <code>/errors</code> - mostra erros recentes",
            "- <code>/add_admin &lt;id&gt; [role] [nome]</code> - adiciona admin",
            "- <code>/remove_admin &lt;id&gt;</code> - remove admin",
        ])
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

    if SUPABASE_ENABLED:
        try:
            from .supabase_client import get_supabase_client

            client = get_supabase_client()
            if client:
                cards_count = str(len(client.get("arkham_cards", {"select": "code"})))
                packs_count = str(len(client.get("arkham_packs", {"select": "code"})))
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
    await update.message.reply_text(_format_status_report(payload), parse_mode=ParseMode.HTML)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /start command."""
    await update.message.reply_text("Hello! Bot started and ready for commands.")


async def card_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Sends a message with inline buttons, listing each pack on a separate line
    for better visualization. Includes a Close button.
    """
    if not await _check_rate_limit(update):
        return ConversationHandler.END

    keyboard_layout = []
    pack_names = list(PACK_CODES.keys())

    for pack_name in pack_names:
        pack_code = PACK_CODES[pack_name]
        button = InlineKeyboardButton(pack_name, callback_data=f"SEARCH_{pack_code}")
        keyboard_layout.append([button])

    close_button = InlineKeyboardButton("Close", callback_data=CALLBACK_CANCEL)
    keyboard_layout.append([close_button])

    reply_markup = InlineKeyboardMarkup(keyboard_layout)

    await update.message.reply_text(
        "Choose a pack to search for the card:",
        reply_markup=reply_markup
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
    if pack_code not in PACK_CODES.values():
        logger.warning(f"Invalid pack callback_data received: {data!r}")
        await query.edit_message_text("Operation canceled. Type /card to start again.")
        context.user_data.clear()
        return ConversationHandler.END

    pack_name = next((name for name, code in PACK_CODES.items() if code == pack_code), f"Code {pack_code}")

    context.user_data['selected_pack_code'] = pack_code

    await query.edit_message_text(
        text=f"Pack **{pack_name}** ({pack_code}) selected!\n"
             f"👉 Please **now enter the card number** you want to search for (Ex: 19, 45, 73, 98, 137):",
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

    pack_name = next((name for name, code in PACK_CODES.items() if code == pack_code), f"code {pack_code}")

    full_card_id = f"{pack_code}{card_number}"
    await update.message.reply_text(f"⏳ Searching for card **{full_card_id}** on ArkhamDB...", parse_mode=ParseMode.MARKDOWN)

    try:
        card_data, source = await get_card_async(full_card_id)
        if not card_data:
            raise ValueError(f"Card not found: {full_card_id}")
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
        message = None

        if card_image_bytes is None:
            await update.message.reply_text(f"⚠️ Card {full_card_id} found, but the front image failed to load. Displaying text only.", parse_mode=ParseMode.MARKDOWN)
            message = await update.message.reply_text(caption, parse_mode=ParseMode.HTML)
        else:
            message = await update.message.reply_photo(
                photo=card_image_bytes,
                caption=caption,
                parse_mode=ParseMode.HTML
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
                            reply_to_message_id=message.message_id
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
                        reply_to_message_id=message.message_id
                    )

    except Exception as e:
        logger.error(f"HTTP Request Error: {e}")
        message_text = (
            f"🚨 Connection Error to ArkhamDB while fetching card **{full_card_id}** "
            f"in expansion '{pack_name}'. Check your connection or try again later."
        )
        await update.message.reply_text(message_text, parse_mode=ParseMode.MARKDOWN)
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    user_id = update.effective_user.id if update.effective_user else None
    await update.message.reply_text(
        _format_help_report(is_admin_user(user_id)),
        parse_mode=ParseMode.HTML,
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    from .local_storage import load_last_pinned_daily_card

    last = load_last_pinned_daily_card()
    if not last:
        await update.message.reply_text("No daily card has been recorded locally yet.")
        return
    await update.message.reply_text(
        f"Last daily card: {last.get('card_code')} — message_id={last.get('message_id')} — date={last.get('posted_date')}"
    )


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    import random
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync

    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
        valid_cards = [c for c in cards if c.get('type_code') not in ['set', 'campaign', 'scenario'] and c.get('spoiler', False) is False]
        card = random.choice(valid_cards)
        await update.message.reply_text(
            f"Random card: {card.get('name') or card.get('real_name')} ({card.get('code')})\nhttps://arkhamdb.com/card/{card.get('code')}"
        )
    except Exception as exc:
        logger.error(f"random_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch a random card right now.")


async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /faq <card_code>")
        return
    import asyncio
    from .arkhamdb_client import fetch_faq_by_card_code_sync

    card_code = context.args[0].strip()
    try:
        faq = await asyncio.to_thread(fetch_faq_by_card_code_sync, card_code)
        if not faq:
            await update.message.reply_text(f"No FAQ found for {card_code}.")
            return
        text = str(faq)
        await update.message.reply_text(text[:3900])
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
        parts.append("Proibida" if dl == 0 else f"Limite {dl}/deck")
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
    'forbidden':   ('🚫', 'Proibidas'),
    'xp_up':       ('⬆️', '+XP (mais caro)'),
    'xp_down':     ('⬇️', '−XP (mais barato)'),
    'exceptional': ('⭐', 'Exceptional'),
    'errata':      ('📝', 'Errata de texto'),
    'other':       ('⚠️', 'Outras restrições'),
}


def _taboo_list_menu_text_and_buttons(taboos: list, name_map: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the taboo list selection message and buttons."""
    sorted_lists = sorted(taboos, key=lambda t: t.get('date_start', ''), reverse=True)
    lines = ["📋 <b>Listas de Taboo</b>", "Selecione uma lista para explorar:\n"]
    buttons = []
    for i, t in enumerate(sorted_lists):
        date = t.get('date_start', '')[:10]
        tid = t.get('id', i)
        label = f"{'✅ ' if i == 0 else ''}{date}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"TABOO_LIST_{tid}")])
    buttons.append([InlineKeyboardButton("❌ Fechar", callback_data=CALLBACK_CANCEL)])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def _taboo_detail_text_and_buttons(taboo: dict, cats: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the category summary for a selected taboo list."""
    date_str = taboo.get('date_start', '')[:10]
    total = sum(len(v) for v in cats.values())
    tid = taboo.get('id', '')
    lines = [f"📋 <b>Taboo — {date_str}</b>", f"{total} carta(s) afetada(s)\n"]
    for cat_key, (icon, label) in TABOO_CATEGORIES.items():
        count = len(cats.get(cat_key, []))
        if count:
            lines.append(f"{icon} {label}: <b>{count}</b>")
    buttons = []
    for cat_key, (icon, label) in TABOO_CATEGORIES.items():
        count = len(cats.get(cat_key, []))
        if count:
            buttons.append([InlineKeyboardButton(f"{icon} {label} ({count})", callback_data=f"TABOO_CAT_{cat_key}_0")])
    buttons.append([InlineKeyboardButton("↩️ Listas", callback_data="TABOO_LISTS")])
    buttons.append([InlineKeyboardButton("❌ Fechar", callback_data=CALLBACK_CANCEL)])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def taboo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync, fetch_taboos_sync

    try:
        taboos, all_cards_raw = await asyncio.gather(
            asyncio.to_thread(fetch_taboos_sync),
            asyncio.to_thread(fetch_all_cards_sync, True),
        )
        if not taboos:
            await update.message.reply_text("Nenhuma lista de taboo encontrada.")
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
                await update.message.reply_text(f"Nenhuma restrição taboo encontrada para «{escape(q)}».", parse_mode=ParseMode.HTML)
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
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)

    except Exception as exc:
        logger.error(f"taboo_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Não foi possível carregar a lista de taboo agora.")


async def taboo_list_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User selected a specific taboo list — show its categories."""
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("TABOO_LIST_", "")
    all_lists = context.bot_data.get('taboo_all_lists', [])
    name_map = context.bot_data.get('taboo_name_map', {})
    taboo = next((t for t in all_lists if str(t.get('id', '')) == tid), None)
    if not taboo:
        await query.answer("Lista não encontrada.", show_alert=True)
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
        await query.answer("Sessão expirada. Use /taboo novamente.", show_alert=True)
        return
    text, markup = _taboo_list_menu_text_and_buttons(all_lists, name_map)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


def _taboo_name(name_map: dict, code: str) -> str:
    v = name_map.get(code, {})
    return v.get('name', code) if isinstance(v, dict) else str(v)

def _taboo_pack(name_map: dict, code: str) -> str:
    v = name_map.get(code, {})
    return v.get('pack', '') if isinstance(v, dict) else ''


async def _send_taboo_card(update: Update, code: str, entry: dict, name_map: dict) -> None:
    """Sends a card image with its taboo restriction info."""
    card, _ = await get_card_async(code)
    name = _taboo_name(name_map, code) or (card.get('name') if card else code)
    restriction = _taboo_restriction_label(entry)
    text_note = entry.get('text') or entry.get('replacement_text') or ''

    if card:
        caption, is_spoiler = _spoiler_caption(card)
        taboo_block = f"\n\n⚠️ <b>Taboo:</b> {escape(restriction)}"
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
        text = f"<b>{escape(name)}</b> (<code>{code}</code>)\n⚠️ <b>Taboo:</b> {escape(restriction)}"
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
    icon, label = TABOO_CATEGORIES.get(cat_key, ('⚠️', cat_key))

    PAGE = 10
    total = len(entries)
    total_pages = max(1, (total + PAGE - 1) // PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = entries[page * PAGE:(page + 1) * PAGE]

    buttons = []
    for code, entry in chunk:
        name = _taboo_name(name_map, code)
        pack = _taboo_pack(name_map, code)
        restriction = _taboo_restriction_label(entry)
        parts = [p for p in [pack, name, code, restriction] if p]
        btn_label = " — ".join(parts)
        if len(btn_label) > 64:
            btn_label = btn_label[:61] + "…"
        buttons.append([InlineKeyboardButton(btn_label, callback_data=f"TABOO_CARD_{code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"TABOO_CAT_{cat_key}_{page-1}"))
    nav.append(InlineKeyboardButton("↩️ Voltar", callback_data="TABOO_BACK"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Próximo", callback_data=f"TABOO_CAT_{cat_key}_{page+1}"))
    buttons.append(nav)

    text = f"{icon} <b>{label}</b> — {total} carta(s) — página {page+1}/{total_pages}:"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def taboo_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    code = query.data.replace("TABOO_CARD_", "")
    by_code = context.bot_data.get('taboo_by_code', {})
    name_map = context.bot_data.get('taboo_name_map', {})
    entry = by_code.get(code)
    if not entry:
        await query.answer("Carta não encontrada na lista de taboo.", show_alert=True)
        return
    await _send_taboo_card(update, code, entry, name_map)


async def taboo_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Back to the selected taboo list's category screen."""
    query = update.callback_query
    await query.answer()
    taboo = context.bot_data.get('taboo_selected', {})
    cats = context.bot_data.get('taboo_cats', {})
    if not taboo:
        await query.answer("Sessão expirada. Use /taboo novamente.", show_alert=True)
        return
    text, markup = _taboo_detail_text_and_buttons(taboo, cats)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def decklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /decklist <decklist_id>")
        return
    import asyncio
    import re
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
                **({"reply_to_message_id": reply_to} if reply_to else {})
            )
        return

    caption, is_spoiler = _spoiler_caption(card)
    image_src = card.get('imagesrc') or card.get('image_src')
    img = await _fetch_card_image(code, image_src)

    if not target:
        return

    reply_to = update.message.message_id if update.message else None
    kwargs = {"reply_to_message_id": reply_to} if reply_to else {}

    if is_spoiler:
        await target.reply_text("⚠️ <b>Atenção: esta carta contém spoiler!</b>", parse_mode=ParseMode.HTML, **kwargs)

    if img:
        front_msg = await target.reply_photo(photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, **kwargs)
    else:
        front_msg = await target.reply_text(caption, parse_mode=ParseMode.HTML, **kwargs)

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
            back_kwargs = {"reply_to_message_id": front_msg.message_id}
            if back_img:
                try:
                    await target.reply_photo(photo=back_img, caption=back_caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, **back_kwargs)
                except Exception:
                    await target.reply_text(back_caption, parse_mode=ParseMode.HTML, **back_kwargs)
            else:
                await target.reply_text(back_caption, parse_mode=ParseMode.HTML, **back_kwargs)

    if prompt_message:
        try:
            await prompt_message.delete()
        except Exception:
            pass


async def search_card_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    card_code = query.data.replace("CARD_SELECT_", "")
    try:
        await query.edit_message_text("🔍 Pesquisando…", parse_mode=ParseMode.HTML)
        card, _ = await get_card_async(card_code)
        if not card:
            await query.edit_message_text("Carta não encontrada.")
            return ConversationHandler.END
        caption, is_spoiler = _spoiler_caption(card)
        image_src = card.get('imagesrc') or card.get('image_src')
        img = await _fetch_card_image(card_code, image_src)
        if is_spoiler:
            await query.message.reply_text("⚠️ <b>Atenção: esta carta contém spoiler!</b>", parse_mode=ParseMode.HTML)
        if img:
            front_msg = await query.message.reply_photo(photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler)
        else:
            front_msg = await query.message.reply_text(caption, parse_mode=ParseMode.HTML)
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
                back_kwargs = {"reply_to_message_id": front_msg.message_id}
                if back_img:
                    try:
                        await query.message.reply_photo(photo=back_img, caption=back_caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, **back_kwargs)
                    except Exception:
                        await query.message.reply_text(back_caption, parse_mode=ParseMode.HTML, **back_kwargs)
                else:
                    await query.message.reply_text(back_caption, parse_mode=ParseMode.HTML, **back_kwargs)
        await query.delete_message()
        _pop_search_prompt(context)
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
        pack = c.get('pack_name') or ''
        spoiler_flag = "⚠️ " if c.get('spoiler') else ""
        label = f"{spoiler_flag}{pack} — {name} — {code}"
        if len(label) > 64:
            label = label[:61] + "…"
        buttons.append([InlineKeyboardButton(label, callback_data=f"CARD_SELECT_{code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"SEARCH_PAGE_{page - 1}"))
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
    """Returns the stored prompt message object and clears all search context keys."""
    prompt = context.user_data.pop("search_prompt_obj", None)
    context.user_data.pop("search_prompt_msg_id", None)
    context.user_data.pop("search_prompt_chat_id", None)
    context.user_data.pop("search_user_msg_id", None)
    context.user_data.pop("search_user_chat_id", None)
    return prompt


async def _search_run(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> int:
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync
    q = query.strip()

    q_lower = q.lower()
    is_numeric = re.fullmatch(r'\d+', q) is not None

    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync, True)  # include encounter cards

        # Exact code match → show card directly (from cache list or API fallback)
        exact = next((c for c in cards if (c.get('code') or '') == q), None)
        if exact or (is_numeric and re.fullmatch(r'\d{5,6}', q)):
            prompt = _pop_search_prompt(context)
            await _send_card_by_code(update, q, prompt_message=prompt)
            return ConversationHandler.END

        if is_numeric:
            matched = [c for c in cards if (c.get('code') or '').startswith(q)]
        else:
            matched = [
                c for c in cards
                if q_lower in (c.get('name') or '').lower()
                or q_lower in (c.get('real_name') or '').lower()
            ]
        results = matched

        if not results:
            msg = "Nenhuma carta encontrada. Tente outro termo."
            if update.message:
                await update.message.reply_text(msg)
            elif update.callback_query:
                await update.callback_query.edit_message_text(msg)
            return ConversationHandler.END

        # Single result → show card directly
        if len(results) == 1:
            prompt = _pop_search_prompt(context)
            await _send_card_by_code(update, results[0]['code'], prompt_message=prompt)
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
        if update.message:
            await update.message.reply_text("Erro ao buscar cartas.")
    return ConversationHandler.END


async def sets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all available packs as inline buttons. Clicking one lists its cards."""
    if not await _check_rate_limit(update):
        return
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync
    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
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
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync
    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
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
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync
    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
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


async def pack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    import asyncio
    from .arkhamdb_client import fetch_cards_by_pack_sync, fetch_packs_sync

    try:
        if not context.args:
            packs = await asyncio.to_thread(fetch_packs_sync)
            text = "Packs:\n" + "\n".join(f"{p.get('code')} — {p.get('name')}" for p in packs[:80])
            await _send_long_or_private(update, text)
            return
        pack_code = context.args[0].strip()
        cards = await asyncio.to_thread(fetch_cards_by_pack_sync, pack_code)
        text = f"Cards in pack {pack_code}:\n" + "\n".join(_card_line(c) for c in cards[:80])
        await _send_long_or_private(update, text)
    except Exception as exc:
        logger.error(f"pack_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch pack data right now.")


async def faction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync, fetch_factions_sync

    try:
        if not context.args:
            factions = await asyncio.to_thread(fetch_factions_sync)
            await update.message.reply_text("Factions:\n" + "\n".join(f"{f.get('code')} — {f.get('name')}" for f in factions))
            return
        faction_code = context.args[0].strip().lower()
        cards = await asyncio.to_thread(fetch_all_cards_sync)
        results = [c for c in cards if str(c.get('faction_code') or '').lower() == faction_code][:80]
        text = f"Cards for faction {faction_code}:\n" + "\n".join(_card_line(c) for c in results)
        await _send_long_or_private(update, text)
    except Exception as exc:
        logger.error(f"faction_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch faction data right now.")


async def type_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /type <type_code>")
        return
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync

    type_code = context.args[0].strip().lower()
    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
        results = [c for c in cards if str(c.get('type_code') or '').lower() == type_code][:80]
        text = f"Cards of type {type_code}:\n" + "\n".join(_card_line(c) for c in results)
        await _send_long_or_private(update, text)
    except Exception as exc:
        logger.error(f"type_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch type data right now.")


async def xp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /xp <number>")
        return
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync

    xp_value = int(context.args[0])
    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
        results = [c for c in cards if c.get('xp') == xp_value][:80]
        text = f"Cards with XP {xp_value}:\n" + "\n".join(_card_line(c) for c in results)
        await _send_long_or_private(update, text)
    except Exception as exc:
        logger.error(f"xp_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch XP data right now.")


async def admin_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    user_id = update.effective_user.id if update.effective_user else None
    await update.message.reply_text(f"Admin access OK. Source: {admin_source(user_id)}")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_status_command(update, context)


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .config import TELEGRAM_CHAT_ID
    chat = update.effective_chat
    await update.message.reply_text(
        f"<b>Chat ID info</b>\n"
        f"Este chat: <code>{chat.id}</code>\n"
        f"TELEGRAM_CHAT_ID (.env): <code>{TELEGRAM_CHAT_ID}</code>\n"
        f"Match: <b>{'✅ SIM' if str(chat.id) == str(TELEGRAM_CHAT_ID) else '❌ NÃO — corrija o .env'}</b>",
        parse_mode=ParseMode.HTML,
    )


async def ai_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tests AI connectivity and reports configuration status."""
    if not await _require_admin(update):
        return
    from .config import AI_DAILY_CARD_ENABLED, AI_MODEL, GEMINI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, OPENAI_API_KEY
    from .repositories.settings_repo import get_setting
    from .ai.daily_card_selector import VALID_MODELS, _OPENAI_COMPAT, _provider, _key_available

    ai_enabled_db = get_setting('ai_enabled', True)
    _model_raw = get_setting('ai_model', None)
    ai_model_db = _model_raw if _model_raw and _model_raw in VALID_MODELS else AI_MODEL
    ai_language = get_setting('ai_language', 'pt-BR')
    provider = _provider(ai_model_db)

    key_status = {
        "GEMINI": bool(GEMINI_API_KEY),
        "OPENAI": bool(OPENAI_API_KEY),
        "GROQ": bool(GROQ_API_KEY),
        "MISTRAL": bool(MISTRAL_API_KEY),
    }
    model_note = f" (DB tinha '{_model_raw}', ignorado)" if _model_raw and _model_raw not in VALID_MODELS else ""
    keys_line = "  ".join(f"{k}: {'✅' if v else '❌'}" for k, v in key_status.items())
    lines = [
        f"<b>AI Diagnostic ({provider.upper()})</b>",
        f"AI habilitada (env): <b>{AI_DAILY_CARD_ENABLED}</b>",
        f"AI habilitada (DB): <b>{ai_enabled_db}</b>",
        f"Model: <b>{ai_model_db}</b>{model_note}",
        f"Provider: <b>{provider}</b>  |  Idioma: <b>{ai_language}</b>",
        f"Chaves: {keys_line}",
        "",
    ]

    if not AI_DAILY_CARD_ENABLED:
        lines.append("AI desabilitada pela variável AI_DAILY_CARD_ENABLED=false")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    elif not _key_available(ai_model_db):
        lines.append(f"Chave {provider.upper()}_API_KEY não configurada no .env do servidor")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    elif not ai_enabled_db:
        lines.append("AI desabilitada no banco — habilite pelo mini app")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    else:
        lines.append(f"Testando conexão {provider.upper()}...")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        try:
            import httpx
            if provider in _OPENAI_COMPAT:
                api_url, get_key = _OPENAI_COMPAT[provider]
                headers = {"Authorization": f"Bearer {get_key()}"}
                req_json = {
                    "model": ai_model_db,
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Say OK"}],
                }
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(api_url, json=req_json, headers=headers)
            else:
                api_url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{ai_model_db}"
                    f":generateContent?key={GEMINI_API_KEY}"
                )
                req_json = {
                    "contents": [{"parts": [{"text": "Say OK"}]}],
                    "generationConfig": {"maxOutputTokens": 5},
                }
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(api_url, json=req_json)
            if resp.status_code == 200:
                await update.message.reply_text(f"✅ {provider.upper()} OK — IA operacional")
            else:
                body = resp.json()
                err = body.get("error", {}).get("message", resp.text[:300])
                await update.message.reply_text(f"❌ {provider.upper()} HTTP {resp.status_code}: {err}")
        except Exception as exc:
            await update.message.reply_text(f"❌ {provider.upper()} falhou: {exc}")


async def post_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /post <card_code>")
        return
    from .daily_card import post_daily_card
    result = await post_daily_card(specific_card_code=context.args[0].strip())
    if result.success:
        await update.message.reply_text(f"Posted {result.card_code}. message_id={result.message_id}")
    else:
        await update.message.reply_text(f"Post failed: {result.error}")


async def repost_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_admin_command(update, context)


async def skip_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /skip <card_code>")
        return
    from .local_storage import save_posted_card
    card_code = context.args[0].strip()
    save_posted_card(card_code)
    await update.message.reply_text(f"Marked as skipped/posted: {card_code}")


async def pause_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .repositories.settings_repo import set_setting
    set_setting("daily_post_enabled", False, updated_by=str(update.effective_user.id if update.effective_user else "telegram"))
    await update.message.reply_text("Daily posting paused.")


async def resume_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .repositories.settings_repo import set_setting
    set_setting("daily_post_enabled", True, updated_by=str(update.effective_user.id if update.effective_user else "telegram"))
    await update.message.reply_text("Daily posting resumed.")


async def settings_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .repositories.settings_repo import get_all_settings
    try:
        settings = get_all_settings()
        if not settings:
            await update.message.reply_text("No Supabase settings loaded or Supabase not configured.")
            return
        import json
        await _send_long_or_private(update, json.dumps(settings, ensure_ascii=False, indent=2), private_threshold=800)
    except Exception as exc:
        logger.error("settings_command_failed: %s", exc, exc_info=True)
        await update.message.reply_text("Could not load settings.")


async def errors_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .repositories.errors_repo import list_recent_errors
    try:
        rows = list_recent_errors(10)
        if rows:
            text = "Recent errors:\n" + "\n".join(f"{r.get('created_at')} — {r.get('context')}: {r.get('error_message')}" for r in rows)
            await _send_long_or_private(update, text)
            return
    except Exception as exc:
        logger.warning("supabase_errors_lookup_failed: %s", exc)
    await update.message.reply_text("No Supabase errors found or Supabase not configured. Check local logs on server.")


async def queue_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .repositories.commands_repo import fetch_pending_commands
    rows = fetch_pending_commands(10)
    if not rows:
        await update.message.reply_text("No pending/retrying commands.")
        return
    text = "Pending commands:\n" + "\n".join(f"{r.get('id')} — {r.get('command_type')} — {r.get('status')}" for r in rows)
    await _send_long_or_private(update, text)


async def sync_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .repositories.commands_repo import enqueue_command
    user_id = update.effective_user.id if update.effective_user else None
    args = context.args or []
    sync_faq = "faq" in args
    cmd = enqueue_command("sync_arkhamdb", payload={"sync_faq": sync_faq}, requested_by=user_id)
    if cmd:
        await update.message.reply_text(
            f"✅ Sync enfileirado (ID: <code>{cmd.get('id', '?')}</code>).\n"
            f"Será executado em até {30}s. Inclui FAQ: {'sim' if sync_faq else 'não'}.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("❌ Falha ao enfileirar sync. Verifique a conexão com o Supabase.")


async def reset_cycle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    from .config import POSTED_CARDS_FILE, POSTED_CARDS_LOCK
    from .local_storage import safe_atomic_write
    safe_atomic_write("", POSTED_CARDS_FILE, POSTED_CARDS_LOCK, data_type="text")
    await update.message.reply_text("Daily card cycle reset locally.")


async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /add_admin <telegram_user_id> [owner|admin|viewer] [name]")
        return
    from .repositories.admins_repo import upsert_admin
    user_id = int(context.args[0])
    role = context.args[1] if len(context.args) >= 2 else "admin"
    name = " ".join(context.args[2:]) if len(context.args) >= 3 else None
    try:
        upsert_admin(user_id, name=name, role=role, enabled=True)
        await update.message.reply_text(f"Admin saved: {user_id} role={role}")
    except Exception as exc:
        await update.message.reply_text(f"Failed to save admin: {exc}")


async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /remove_admin <telegram_user_id>")
        return
    from .repositories.admins_repo import disable_admin
    user_id = int(context.args[0])
    disable_admin(user_id)
    await update.message.reply_text(f"Admin disabled: {user_id}")


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
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("random", random_command))
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
    application.add_handler(CommandHandler("pack", pack_command))
    application.add_handler(CommandHandler("faction", faction_command))
    application.add_handler(CommandHandler("type", type_command))
    application.add_handler(CommandHandler("xp", xp_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("admin_status", admin_status_command))
    application.add_handler(CommandHandler("ai_test", ai_test_command))
    application.add_handler(CommandHandler("chatid", chatid_command))
    application.add_handler(CommandHandler("post", post_admin_command))
    application.add_handler(CommandHandler("repost", repost_admin_command))
    application.add_handler(CommandHandler("skip", skip_admin_command))
    application.add_handler(CommandHandler("pause", pause_admin_command))
    application.add_handler(CommandHandler("resume", resume_admin_command))
    application.add_handler(CommandHandler("settings", settings_admin_command))
    application.add_handler(CommandHandler("errors", errors_admin_command))
    application.add_handler(CommandHandler("queue", queue_admin_command))
    application.add_handler(CommandHandler("sync", sync_admin_command))
    application.add_handler(CommandHandler("reset_cycle", reset_cycle_admin_command))
    application.add_handler(CommandHandler("add_admin", add_admin_command))
    application.add_handler(CommandHandler("remove_admin", remove_admin_command))
    application.add_handler(card_conv_handler)
    application.add_handler(CommandHandler("cancel", cancel_conversation))
    application.add_handler(CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"))
    application.add_error_handler(error_handler)
