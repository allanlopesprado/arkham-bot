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
        f"- Ultima carta: {_code(payload['last_daily_post_card_code'])}",
        "",
        "<b>Dados</b>",
        f"- Supabase: {_bold(payload['supabase_status'])}",
        f"- Cartas: {_code(payload['cards_count'])}",
        f"- Packs: {_code(payload['packs_count'])}",
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
        BOT_COMMANDS_POLLING_ENABLED,
        DAILY_POST_DAYS,
        DAILY_POST_ENABLED,
        DAILY_POST_TIMES,
        DAILY_SCHEDULER_STATE_FILE,
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
        "last_daily_post_status": state.get("last_daily_post_status", "-"),
        "last_daily_post_card_code": state.get("last_daily_post_card_code", "-"),
        "supabase_configured": SUPABASE_ENABLED,
        "supabase_status": supabase_status,
        "cards_count": cards_count,
        "packs_count": packs_count,
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
        await query.edit_message_text("Operation canceled. Type /card to start again.")
    else:
        await update.message.reply_text("Operation canceled. Type /card to start again.")

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


async def taboo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    import asyncio
    from .arkhamdb_client import fetch_taboos_sync

    try:
        taboos = await asyncio.to_thread(fetch_taboos_sync)
        if isinstance(taboos, list):
            await update.message.reply_text(f"Taboo lists available: {len(taboos)}")
        elif isinstance(taboos, dict):
            await update.message.reply_text(f"Taboo data loaded. Keys: {', '.join(sorted(taboos.keys())[:20])}")
        else:
            await update.message.reply_text("No taboo data found.")
    except Exception as exc:
        logger.error(f"taboo_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not fetch taboo data right now.")


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


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /search <name>")
        return
    import asyncio
    from .arkhamdb_client import fetch_all_cards_sync

    query = " ".join(context.args).strip().lower()
    try:
        cards = await asyncio.to_thread(fetch_all_cards_sync)
        results = [
            c for c in cards
            if query in (c.get('name') or '').lower() or query in (c.get('real_name') or '').lower()
        ][:20]
        if not results:
            await update.message.reply_text("No cards found.")
            return
        text = "Search results:\n" + "\n".join(_card_line(c) for c in results)
        await _send_long_or_private(update, text, private_threshold=900 if len(results) > 5 else 1800)
    except Exception as exc:
        logger.error(f"search_command_failed: {exc}", exc_info=True)
        await update.message.reply_text("Could not search cards right now.")


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
    await update.message.reply_text("Sync must be run on the server/CI: python scripts/sync_arkhamdb.py --dry-run, then without --dry-run.")


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
    application.add_handler(CommandHandler("decklist", decklist_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("pack", pack_command))
    application.add_handler(CommandHandler("faction", faction_command))
    application.add_handler(CommandHandler("type", type_command))
    application.add_handler(CommandHandler("xp", xp_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("admin_status", admin_status_command))
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
    application.add_error_handler(error_handler)
