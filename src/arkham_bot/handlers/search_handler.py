import asyncio
import logging
import re
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from ..core.config import CALLBACK_CANCEL, SEARCH_WAITING_QUERY
from ..formatters.text_formatters import format_card_back_caption
from ..i18n import get_strings
from ..services.card_provider import get_card_async
from .common import (
    _abbrev_pack,
    _check_rate_limit,
    _fetch_all_cards,
    _fetch_card_image,
    _pop_search_prompt,
    _spoiler_caption,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


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
                get_strings()["search_card_not_found_code"].format(code=escape(code)),
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

    user_msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not user_msg:
        return

    if is_spoiler:
        await user_msg.reply_text(get_strings()["search_spoiler_warning"], parse_mode=ParseMode.HTML, do_quote=True)

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
            if back_img:
                try:
                    await front_msg.reply_photo(photo=back_img, caption=back_caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, do_quote=True)
                except Exception:
                    await front_msg.reply_text(back_caption, parse_mode=ParseMode.HTML, do_quote=True)
            else:
                await front_msg.reply_text(back_caption, parse_mode=ParseMode.HTML, do_quote=True)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_rate_limit(update):
        return ConversationHandler.END
    if context.args:
        context.user_data["search_user_msg_id"] = update.message.message_id
        return await _search_run(update, context, " ".join(context.args).strip())
    s = get_strings()
    prompt = await update.message.reply_text(
        s["search_prompt"],
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(s["search_btn_cancel"], callback_data=CALLBACK_CANCEL)
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
    s = get_strings()
    if not query:
        await update.message.reply_text(s["search_empty_query"])
        return SEARCH_WAITING_QUERY
    if len(query) < 2:
        await update.message.reply_text(s.get("search_query_too_short", s["search_empty_query"]))
        return SEARCH_WAITING_QUERY
    old_prompt = context.user_data.pop("search_prompt_obj", None)
    context.user_data.pop("search_prompt_msg_id", None)
    context.user_data.pop("search_prompt_chat_id", None)
    if old_prompt:
        try:
            await old_prompt.delete()
        except Exception:
            pass
    context.user_data["search_user_msg_id"] = update.message.message_id
    searching_msg = await update.message.reply_text(s["search_searching"])
    context.user_data["search_prompt_obj"] = searching_msg
    return await _search_run(update, context, query)


async def search_card_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    card_code = query.data.replace("CARD_SELECT_", "")
    user_id = update.effective_user.id if update.effective_user else 0
    user_msg_id = context.user_data.get("search_user_msg_id")
    if not user_msg_id and query.message and query.message.reply_to_message:
        user_msg_id = query.message.reply_to_message.message_id
    try:
        card, _ = await get_card_async(card_code)
        if not card:
            await query.edit_message_text(get_strings()["search_card_not_found"])
            return ConversationHandler.END
        caption, is_spoiler = _spoiler_caption(card)
        image_src = card.get('imagesrc') or card.get('image_src')
        img = await _fetch_card_image(card_code, image_src)
        try:
            await query.delete_message()
        except Exception:
            pass
        _pop_search_prompt(context)
        context.bot_data.pop(f"search_{user_id}", None)
        bot = query.message.get_bot()
        chat_id = query.message.chat_id
        rp = ReplyParameters(message_id=user_msg_id) if user_msg_id else None
        if is_spoiler:
            await bot.send_message(chat_id=chat_id, text=get_strings()["search_spoiler_warning"], parse_mode=ParseMode.HTML, reply_parameters=rp)
        if img:
            front_msg = await bot.send_photo(chat_id=chat_id, photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, reply_parameters=rp)
        else:
            front_msg = await bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.HTML, reply_parameters=rp)
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
            await query.edit_message_text(get_strings()["search_card_load_error"])
        except Exception:
            pass
    return ConversationHandler.END


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

    s = get_strings()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(s["search_btn_previous"], callback_data=f"SEARCH_PAGE_{page - 1}"))
    nav.append(InlineKeyboardButton(s["search_btn_cancel_nav"], callback_data=CALLBACK_CANCEL))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(s["search_btn_next"], callback_data=f"SEARCH_PAGE_{page + 1}"))
    buttons.append(nav)

    text = s["search_results"].format(total=total, query=escape(query), page=page + 1, total_pages=total_pages)
    return InlineKeyboardMarkup(buttons), text


async def search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("SEARCH_PAGE_", ""))
    user_id = update.effective_user.id
    results = context.bot_data.get(f"search_{user_id}")
    if not results:
        await query.edit_message_text(get_strings()["search_session_expired"])
        return
    msg_text = query.message.text or ""
    raw_query = ""
    try:
        if "«" in msg_text and "»" in msg_text:
            raw_query = msg_text.split("«")[1].split("»")[0]
    except (IndexError, ValueError):
        pass
    markup, text = _search_page(results, page=page, query=raw_query)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def _search_run(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> int:
    from ..repositories.cards_repo import search_cards

    q = query.strip()
    is_numeric = re.fullmatch(r'\d+', q) is not None
    is_card_code = re.fullmatch(r'\d{4,6}[a-z]?', q) is not None

    try:
        if is_card_code:
            prompt = _pop_search_prompt(context)
            await _send_card_by_code(update, q, prompt_message=prompt)
            return ConversationHandler.END

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

        if len(results) == 1 or (results and results[0].get('code') == q):
            exact = next((c for c in results if (c.get('code') or '') == q), None)
            if exact or len(results) == 1:
                code = (exact or results[0]).get('code', q)
                prompt = _pop_search_prompt(context)
                await _send_card_by_code(update, code, prompt_message=prompt)
                return ConversationHandler.END

        searching_msg = _pop_search_prompt(context)
        async def _delete_searching():
            if searching_msg:
                try:
                    await searching_msg.delete()
                except Exception:
                    pass
        await _delete_searching()

        if not results:
            msg = get_strings()["search_not_found"]
            if update.message:
                await update.message.reply_text(msg)
            elif update.callback_query:
                await update.callback_query.edit_message_text(msg)
            return ConversationHandler.END

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
            await update.message.reply_text(get_strings()["search_error"])
    return ConversationHandler.END
