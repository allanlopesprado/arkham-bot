import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.error import BadRequest as TelegramBadRequest
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..core.config import CALLBACK_CANCEL
from ..i18n import get_strings
from .common import (
    _SETS_PAGE_SIZE,
    _check_rate_limit,
    _fetch_all_cards,
)

logger = logging.getLogger(__name__)


def _sets_pack_list(cards: list) -> list[tuple[str, str, int]]:
    seen: dict[str, str] = {}
    counts: dict[str, int] = {}
    for c in cards:
        code = c.get('pack_code') or ''
        name = c.get('pack_name') or code
        if code:
            if code not in seen:
                seen[code] = name
            counts[code] = counts.get(code, 0) + 1
    return [(code, name, counts.get(code, 0)) for code, name in seen.items()]


def _sets_pack_buttons(packs: list[tuple[str, str, int]], page: int, s: dict) -> InlineKeyboardMarkup:
    start = page * _SETS_PAGE_SIZE
    page_packs = packs[start:start + _SETS_PAGE_SIZE]
    buttons = [
        [InlineKeyboardButton(f"{name} ({count})", callback_data=f"SET_BROWSE_{code}_p0")]
        for code, name, count in page_packs
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(s.get("sets_btn_prev", "◀"), callback_data=f"SET_LIST_p{page - 1}"))
    if start + _SETS_PAGE_SIZE < len(packs):
        nav.append(InlineKeyboardButton(s.get("sets_btn_next", "▶"), callback_data=f"SET_LIST_p{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(s.get("card_btn_close", "Fechar"), callback_data=CALLBACK_CANCEL)])
    return InlineKeyboardMarkup(buttons)


async def sets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all available packs as inline buttons with pagination."""
    if not await _check_rate_limit(update):
        return
    try:
        cards = await _fetch_all_cards()
        packs = _sets_pack_list(cards)
        s = get_strings()
        if not packs:
            await update.message.reply_text(s["sets_no_sets"])
            return
        total = len(packs)
        text = s["sets_choose"] + f" ({total})"
        await update.message.reply_text(
            text,
            reply_markup=_sets_pack_buttons(packs, 0, s),
            reply_parameters=ReplyParameters(message_id=update.message.message_id),
        )
    except Exception as exc:
        logger.error(f"sets_command error: {exc}", exc_info=True)
        await update.message.reply_text(get_strings()["sets_error"])


async def set_browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows cards of the selected pack as inline buttons with pagination."""
    query = update.callback_query
    await query.answer()
    data = query.data.replace("SET_BROWSE_", "")
    page = 0
    if "_p" in data:
        parts = data.rsplit("_p", 1)
        pack_code = parts[0]
        try:
            page = int(parts[1])
        except ValueError:
            pack_code = data
    else:
        pack_code = data
    try:
        cards = await _fetch_all_cards()
        pack_cards = [c for c in cards if c.get('pack_code') == pack_code]
        s = get_strings()
        if not pack_cards:
            await query.edit_message_text(s["sets_no_cards"])
            return
        pack_name = pack_cards[0].get('pack_name') or pack_code
        total = len(pack_cards)
        start = page * _SETS_PAGE_SIZE
        page_cards = pack_cards[start:start + _SETS_PAGE_SIZE]
        buttons = []
        for c in page_cards:
            code = c.get('code', '')
            name = c.get('name') or c.get('real_name') or code
            position = c.get('position', '')
            label = f"{position}. {name}" if position else name
            if len(label) > 60:
                label = label[:57] + "…"
            buttons.append([InlineKeyboardButton(label, callback_data=f"CARD_SELECT_{code}")])
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(s.get("sets_btn_prev", "◀"), callback_data=f"SET_BROWSE_{pack_code}_p{page - 1}"))
        if start + _SETS_PAGE_SIZE < total:
            nav.append(InlineKeyboardButton(s.get("sets_btn_next", "▶"), callback_data=f"SET_BROWSE_{pack_code}_p{page + 1}"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton(s["sets_btn_back"], callback_data="SETS_BACK_p0")])
        page_info = f" — {start + 1}–{min(start + _SETS_PAGE_SIZE, total)}/{total}"
        await query.edit_message_text(
            s["sets_pack_title"].format(pack_name=escape(pack_name), count=total) + page_info,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as exc:
        logger.error(f"set_browse_callback error: {exc}", exc_info=True)
        await query.edit_message_text(get_strings()["sets_pack_error"])


async def sets_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Navigates pack list pages."""
    query = update.callback_query
    await query.answer()
    try:
        page = int(query.data.replace("SET_LIST_p", ""))
    except ValueError:
        page = 0
    try:
        cards = await _fetch_all_cards()
        packs = _sets_pack_list(cards)
        s = get_strings()
        total = len(packs)
        try:
            await query.edit_message_text(
                s["sets_choose"] + f" ({total})",
                reply_markup=_sets_pack_buttons(packs, page, s),
            )
        except TelegramBadRequest:
            pass
    except Exception as exc:
        logger.error(f"sets_list_page_callback error: {exc}", exc_info=True)


async def sets_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns to the pack list at the given page."""
    query = update.callback_query
    await query.answer()
    data = query.data  # SETS_BACK_p{page}
    page = 0
    if "_p" in data:
        try:
            page = int(data.rsplit("_p", 1)[1])
        except ValueError:
            pass
    try:
        cards = await _fetch_all_cards()
        packs = _sets_pack_list(cards)
        s = get_strings()
        total = len(packs)
        text = s["sets_choose"] + f" ({total})"
        try:
            await query.edit_message_text(text, reply_markup=_sets_pack_buttons(packs, page, s))
        except TelegramBadRequest:
            pass
    except Exception as exc:
        logger.error(f"sets_back_callback error: {exc}", exc_info=True)
