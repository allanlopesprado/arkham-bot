import asyncio
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.error import BadRequest as TelegramBadRequest
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from ..core.config import CALLBACK_CANCEL, CHOOSING_CARD_NUMBER
from ..core.supabase_client import get_supabase_client
from ..formatters.text_formatters import format_card_back_caption
from ..i18n import get_strings
from ..services.card_provider import get_card_async
from .common import (
    _CARD_PAGE_SIZE,
    _check_rate_limit,
    _fetch_card_image,
    _get_cached_pack_list,
    _spoiler_caption,
)

import random

logger = logging.getLogger(__name__)

_pack_positions_cache: dict[str, tuple[int, int, int, list[int], set[int]]] = {}


def _get_pack_positions(pack_code_prefix: str) -> tuple[int, int, int, list[int], set[int]]:
    """Returns (count, min_num, max_num, sample_numbers, valid_numbers_set)."""
    cached = _pack_positions_cache.get(pack_code_prefix)
    if cached is not None:
        return cached
    try:
        client = get_supabase_client()
        if not client:
            return 0, 0, 0, [], set()
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
            return 0, 0, 0, [], set()
        sample_pool = [n for n in numbers if n > 0] or numbers
        k = min(5, len(sample_pool))
        sample = sorted(random.sample(sample_pool, k))
        result = (len(numbers), numbers[0], numbers[-1], sample, set(numbers))
        _pack_positions_cache[pack_code_prefix] = result
        return result
    except Exception as exc:
        logger.warning(f"Failed to get pack positions for {pack_code_prefix}: {exc}")
        return 0, 0, 0, [], set()


def _card_pack_buttons(packs: list, page: int, s: dict) -> InlineKeyboardMarkup:
    start = page * _CARD_PAGE_SIZE
    page_packs = packs[start:start + _CARD_PAGE_SIZE]
    buttons = [
        [InlineKeyboardButton(f"{p['display_name']} ({p['card_count']})", callback_data=f"SEARCH_{p['prefix']}")]
        for p in page_packs
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(s.get("sets_btn_prev", "◀"), callback_data=f"CARD_LIST_p{page - 1}"))
    if start + _CARD_PAGE_SIZE < len(packs):
        nav.append(InlineKeyboardButton(s.get("sets_btn_next", "▶"), callback_data=f"CARD_LIST_p{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(s["card_btn_close"], callback_data=CALLBACK_CANCEL)])
    return InlineKeyboardMarkup(buttons)


async def card_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lists packs with pagination for card search."""
    if not await _check_rate_limit(update):
        return ConversationHandler.END

    packs = await asyncio.to_thread(_get_cached_pack_list)
    s = get_strings()
    await update.message.reply_text(
        s["card_choose_pack"],
        reply_markup=_card_pack_buttons(packs, 0, s),
        reply_parameters=ReplyParameters(message_id=update.message.message_id),
    )
    return CHOOSING_CARD_NUMBER


async def card_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigates pack list pages in /card."""
    query = update.callback_query
    await query.answer()
    try:
        page = int(query.data.replace("CARD_LIST_p", ""))
    except ValueError:
        page = 0
    packs = await asyncio.to_thread(_get_cached_pack_list)
    s = get_strings()
    try:
        await query.edit_message_text(
            s["card_choose_pack"],
            reply_markup=_card_pack_buttons(packs, page, s),
        )
    except TelegramBadRequest:
        pass
    return CHOOSING_CARD_NUMBER


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the chosen pack and instructs the user to type the card number."""
    query = update.callback_query
    await query.answer()

    s = get_strings()
    data = query.data
    if not data or not data.startswith("SEARCH_"):
        logger.warning(f"Unknown callback_data received: {data!r}")
        await query.edit_message_text(s["card_canceled"])
        context.user_data.clear()
        return ConversationHandler.END

    pack_code = data[len("SEARCH_"):]
    packs = await asyncio.to_thread(_get_cached_pack_list)
    pack_entry = next((p for p in packs if p['prefix'] == pack_code), None)
    if not pack_entry:
        logger.warning(f"Invalid pack callback_data received: {data!r}")
        await query.edit_message_text(s["card_canceled"])
        context.user_data.clear()
        return ConversationHandler.END

    pack_name = pack_entry['display_name']

    context.user_data['selected_pack_code'] = pack_code

    count, min_pos, max_pos, sample, valid_numbers = await asyncio.to_thread(_get_pack_positions, pack_code)
    context.user_data['pack_valid_numbers'] = valid_numbers

    if count > 0:
        sample_str = ", ".join(str(p) for p in sample)
        card_info = f"({count} cards)"
        example_hint = f"Ex: {sample_str}"
    else:
        card_info = ""
        example_hint = s["card_example_fallback"]

    cancel_button = InlineKeyboardButton(s["card_btn_close"], callback_data=CALLBACK_CANCEL)
    await query.edit_message_text(
        text=s["card_pack_selected"].format(pack_name=pack_name, card_info=card_info, example_hint=example_hint),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[cancel_button]]),
    )

    return CHOOSING_CARD_NUMBER


async def receive_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes the card number, searches the API, and returns the name/image."""
    card_number_input = update.message.text.strip()

    s = get_strings()
    if not card_number_input.isalnum() and not any(c.isdigit() for c in card_number_input):
        await update.message.reply_text(s["card_invalid_input"])
        return CHOOSING_CARD_NUMBER

    if len(card_number_input) > 5:
        await update.message.reply_text(s["card_input_too_long"])
        return CHOOSING_CARD_NUMBER

    card_number = card_number_input
    entered_int = None
    try:
        entered_int = int(card_number_input)
        card_number = card_number_input.zfill(3)
    except ValueError:
        pass

    pack_code = context.user_data.get('selected_pack_code')

    if entered_int is not None and pack_code:
        valid_numbers: set[int] = context.user_data.get('pack_valid_numbers', set())
        if valid_numbers and entered_int not in valid_numbers:
            nearby = sorted(n for n in valid_numbers if abs(n - entered_int) <= 50)[:6] or sorted(valid_numbers)[:6]
            samples_str = ", ".join(str(n) for n in nearby)
            await update.message.reply_text(
                s["card_number_not_in_pack"].format(number=entered_int, samples=samples_str),
                parse_mode=ParseMode.MARKDOWN,
            )
            return CHOOSING_CARD_NUMBER

    if not pack_code:
        await update.message.reply_text(s["card_no_pack"])
        context.user_data.clear()
        return ConversationHandler.END

    full_card_id = f"{pack_code}{card_number}"
    user_msg_id = update.message.message_id
    user_reply = ReplyParameters(message_id=user_msg_id)

    status_msg = await update.message.reply_text(
        s["card_searching"].format(full_card_id=full_card_id),
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
            await _update_status(s["card_not_found"].format(full_card_id=full_card_id))
            context.user_data.clear()
            return ConversationHandler.END
        logger.info(f"Card {full_card_id} loaded from {source}")
        card_code = card_data.get('code')

        image_src = card_data.get('imagesrc') or card_data.get('image_src')
        card_image_bytes = await _fetch_card_image(card_code, image_src)

        caption, is_spoiler = _spoiler_caption(card_data)
        await _delete_status()
        message = None

        if is_spoiler:
            await update.message.reply_text(get_strings()["search_spoiler_warning"], parse_mode=ParseMode.HTML, reply_parameters=user_reply)

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
                has_spoiler=is_spoiler,
                reply_parameters=user_reply,
            )

        if card_data.get('double_sided') and message:
            back_image_src = card_data.get('backimagesrc')
            back_text_raw = card_data.get('back_text')
            back_flavor_raw = card_data.get('back_flavor')

            if back_text_raw or back_flavor_raw:
                back_caption = format_card_back_caption(card_data, back_text_raw, is_interactive=True)
                back_image_bytes = await _fetch_card_image(f"{card_code}b", back_image_src)
                found_back_image = back_image_bytes is not None

                if found_back_image:
                    try:
                        await update.message.reply_photo(
                            photo=back_image_bytes,
                            caption=back_caption,
                            parse_mode=ParseMode.HTML,
                            has_spoiler=is_spoiler,
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
        await _update_status(s["card_error"].format(full_card_id=full_card_id))
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
            s = get_strings()
            await query.edit_message_text(s["cancel_closed"])
    else:
        s = get_strings()
        await update.message.reply_text(s["cancel_text"])

    context.user_data.clear()
    return ConversationHandler.END
