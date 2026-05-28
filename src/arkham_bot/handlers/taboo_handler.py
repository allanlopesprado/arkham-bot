import asyncio
import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.error import BadRequest as TelegramBadRequest
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..core.config import CALLBACK_CANCEL
from ..i18n import get_strings
from ..services.card_provider import get_card_async
from .common import (
    _TABOO_PAGE_SIZE,
    _check_rate_limit,
    _fetch_all_cards,
    _fetch_all_taboos,
    _fetch_card_image,
    _spoiler_caption,
)

logger = logging.getLogger(__name__)

TABOO_CATEGORY_KEYS = ['forbidden', 'xp_up', 'xp_down', 'exceptional', 'errata', 'other']


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
    s = get_strings()
    parts = []
    xp = entry.get('xp')
    if xp is not None:
        parts.append(f"{'+'if xp>0 else ''}{xp} XP")
    dl = entry.get('deck_limit')
    if dl is not None:
        parts.append(s["taboo_label_banned"] if dl == 0 else s["taboo_label_limit"].format(n=dl))
    if entry.get('exceptional'):
        parts.append(s["taboo_label_exceptional"])
    if entry.get('text') or entry.get('replacement_text'):
        parts.append(s["taboo_label_errata"])
    return " · ".join(parts) if parts else s["taboo_label_restricted"]


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


def _taboo_categories() -> dict[str, tuple[str, str]]:
    """Returns TABOO_CATEGORIES dict with localized labels."""
    s = get_strings()
    return {
        'forbidden':   ('', s['taboo_cat_forbidden']),
        'xp_up':       ('', s['taboo_cat_xp_up']),
        'xp_down':     ('', s['taboo_cat_xp_down']),
        'exceptional': ('', s['taboo_cat_exceptional']),
        'errata':      ('', s['taboo_cat_errata']),
        'other':       ('', s['taboo_cat_other']),
    }


def _taboo_name(name_map: dict, code: str) -> str:
    v = name_map.get(code, {})
    return v.get('name', code) if isinstance(v, dict) else str(v)


def _taboo_list_menu_text_and_buttons(taboos: list, name_map: dict, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the taboo list selection message and buttons with pagination."""
    s = get_strings()
    sorted_lists = sorted(taboos, key=lambda t: t.get('date_start', ''), reverse=True)
    total = len(sorted_lists)
    start = page * _TABOO_PAGE_SIZE
    page_lists = sorted_lists[start:start + _TABOO_PAGE_SIZE]
    lines = [s["taboo_lists_title"], s["taboo_lists_subtitle"]]
    buttons = []
    for i, t in enumerate(page_lists):
        raw = t.get('date_start', '')[:10]
        date = f"{raw[8:10]}/{raw[5:7]}/{raw[:4]}" if len(raw) == 10 else raw
        tid = t.get('id', start + i)
        is_current = (start + i == 0)
        label = f"{s['taboo_list_current_prefix'].strip()} {date}" if is_current else date
        buttons.append([InlineKeyboardButton(label, callback_data=f"TABOO_LIST_{tid}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(s.get("sets_btn_prev", "◀"), callback_data=f"TABOO_PAGE_{page - 1}"))
    if start + _TABOO_PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(s.get("sets_btn_next", "▶"), callback_data=f"TABOO_PAGE_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(s["taboo_btn_close"], callback_data=CALLBACK_CANCEL)])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def _taboo_detail_text_and_buttons(taboo: dict, cats: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the category summary for a selected taboo list."""
    s = get_strings()
    TABOO_CATEGORIES = _taboo_categories()
    raw_date = taboo.get('date_start', '')[:10]
    date_str = f"{raw_date[8:10]}/{raw_date[5:7]}/{raw_date[:4]}" if len(raw_date) == 10 else raw_date
    total = sum(len(v) for v in cats.values())
    lines = [s["taboo_detail_title"].format(date=date_str), s["taboo_detail_affected"].format(total=total)]
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
        InlineKeyboardButton(s["taboo_btn_lists"], callback_data="TABOO_LISTS"),
        InlineKeyboardButton(s["taboo_btn_close"], callback_data=CALLBACK_CANCEL),
    ])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def _send_taboo_card(update: Update, code: str, entry: dict, name_map: dict, reply_to=None) -> None:
    """Sends a card image with its taboo restriction info."""
    card, _ = await get_card_async(code)
    name = _taboo_name(name_map, code) or (card.get('name') if card else code)
    restriction = _taboo_restriction_label(entry)
    text_note = entry.get('text') or entry.get('replacement_text') or ''

    target = reply_to or update.message or (update.callback_query.message if update.callback_query else None)
    if not target:
        return

    reply_params = ReplyParameters(message_id=target.message_id)

    if card:
        caption, is_spoiler = _spoiler_caption(card)
        taboo_block = f"\n\n<b>Taboo:</b> {escape(restriction)}"
        if text_note:
            taboo_block += f"\n<i>{escape(text_note)}</i>"
        caption = caption + taboo_block
        image_src = card.get('imagesrc') or card.get('image_src')
        img = await _fetch_card_image(code, image_src)
        if img:
            await target.reply_photo(photo=img, caption=caption, parse_mode=ParseMode.HTML, has_spoiler=is_spoiler, reply_parameters=reply_params)
        else:
            await target.reply_text(caption, parse_mode=ParseMode.HTML, reply_parameters=reply_params)
    else:
        text = f"<b>{escape(name)}</b> (<code>{code}</code>)\n<b>Taboo:</b> {escape(restriction)}"
        if text_note:
            text += f"\n<i>{escape(text_note)}</i>"
        await target.reply_text(text, parse_mode=ParseMode.HTML, reply_parameters=reply_params)


async def taboo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    try:
        taboos, all_cards_raw = await asyncio.gather(
            _fetch_all_taboos(),
            _fetch_all_cards(include_encounter=True),
        )
        if not taboos:
            s = get_strings()
            await update.message.reply_text(s["taboo_no_lists"])
            return

        name_map = {c['code']: {'name': c.get('name') or c.get('real_name') or c['code'], 'pack': c.get('pack_name') or ''} for c in all_cards_raw if c.get('code')}
        sorted_lists = sorted(taboos, key=lambda t: t.get('date_start', ''), reverse=True)
        context.bot_data['taboo_all_lists'] = sorted_lists
        context.bot_data['taboo_name_map'] = name_map

        if context.args:
            q = " ".join(context.args).strip().lower()
            by_code = _parse_taboo_cards(sorted_lists[0])
            matches = {code: entry for code, entry in by_code.items()
                       if q in _taboo_name(name_map, code).lower() or q == code.lower()}
            s = get_strings()
            if not matches:
                await update.message.reply_text(s["taboo_not_found_for"].format(query=escape(q)), parse_mode=ParseMode.HTML)
                return
            if len(matches) == 1:
                code, entry = next(iter(matches.items()))
                await _send_taboo_card(update, code, entry, name_map)
                return
            lines = [s["taboo_results_title"].format(query=escape(q))]
            for code, entry in list(matches.items())[:20]:
                lines.append(f"• <b>{escape(_taboo_name(name_map, code))}</b> ({code}) — {escape(_taboo_restriction_label(entry))}")
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
            return

        context.bot_data['taboo_origin_chat_id'] = update.message.chat_id
        context.bot_data['taboo_origin_message_id'] = update.message.message_id

        latest = sorted_lists[0]
        by_code = _parse_taboo_cards(latest)
        cats: dict[str, list] = {k: [] for k in TABOO_CATEGORY_KEYS}
        for code, entry in by_code.items():
            cat = _taboo_category(entry)
            cats.setdefault(cat, []).append((code, entry))
        context.bot_data['taboo_selected'] = latest
        context.bot_data['taboo_by_code'] = by_code
        context.bot_data['taboo_cats'] = cats

        text, markup = _taboo_detail_text_and_buttons(latest, cats)
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
            reply_parameters=ReplyParameters(message_id=update.message.message_id),
        )

    except Exception as exc:
        logger.error(f"taboo_command_failed: {exc}", exc_info=True)
        s = get_strings()
        await update.message.reply_text(s["taboo_error"])


async def taboo_list_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User selected a specific taboo list — show its categories."""
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("TABOO_LIST_", "")
    all_lists = context.bot_data.get('taboo_all_lists', [])
    name_map = context.bot_data.get('taboo_name_map', {})
    taboo = next((t for t in all_lists if str(t.get('id', '')) == tid), None)
    if not taboo:
        s = get_strings()
        await query.answer(s["taboo_list_not_found"], show_alert=True)
        return
    by_code = _parse_taboo_cards(taboo)
    cats: dict[str, list] = {k: [] for k in TABOO_CATEGORY_KEYS}
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
        s = get_strings()
        await query.answer(s["taboo_session_expired"], show_alert=True)
        return
    text, markup = _taboo_list_menu_text_and_buttons(all_lists, name_map, page=0)
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    except TelegramBadRequest:
        pass


async def taboo_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Navigates taboo list pages."""
    query = update.callback_query
    await query.answer()
    try:
        page = int(query.data.replace("TABOO_PAGE_", ""))
    except ValueError:
        page = 0
    all_lists = context.bot_data.get('taboo_all_lists', [])
    name_map = context.bot_data.get('taboo_name_map', {})
    if not all_lists:
        await query.answer(get_strings()["taboo_session_expired"], show_alert=True)
        return
    text, markup = _taboo_list_menu_text_and_buttons(all_lists, name_map, page=page)
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    except TelegramBadRequest:
        pass


async def taboo_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.replace("TABOO_CAT_", "").rsplit("_", 1)
    cat_key = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0

    cats = context.bot_data.get('taboo_cats', {})
    name_map = context.bot_data.get('taboo_name_map', {})
    entries = cats.get(cat_key, [])
    TABOO_CATEGORIES = _taboo_categories()
    icon, label = TABOO_CATEGORIES.get(cat_key, ('', cat_key))
    s = get_strings()

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
    btn_prev = InlineKeyboardButton(s["taboo_btn_previous"], callback_data=f"TABOO_CAT_{cat_key}_{page-1}")
    btn_next = InlineKeyboardButton(s["taboo_btn_next"], callback_data=f"TABOO_CAT_{cat_key}_{page+1}")
    btn_back = InlineKeyboardButton(s["taboo_btn_back"], callback_data="TABOO_BACK")
    btn_close = InlineKeyboardButton(s["taboo_btn_close"], callback_data=CALLBACK_CANCEL)
    if has_prev and has_next:
        buttons.append([btn_prev, btn_close, btn_next])
    elif has_prev:
        buttons.append([btn_prev, btn_back, btn_close])
    elif has_next:
        buttons.append([btn_close, btn_next])
    else:
        buttons.append([btn_back, btn_close])

    text = s["taboo_category_page"].format(label=label, total=total, page=page+1, total_pages=total_pages)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def taboo_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    code = query.data.replace("TABOO_CARD_", "")
    by_code = context.bot_data.get('taboo_by_code', {})
    name_map = context.bot_data.get('taboo_name_map', {})
    entry = by_code.get(code)
    s = get_strings()
    if not entry:
        await query.answer(s["taboo_card_not_found"], show_alert=True)
        return

    await query.edit_message_text(s["taboo_card_searching"].format(code=code), parse_mode=ParseMode.HTML)

    origin_chat_id = context.bot_data.get('taboo_origin_chat_id')
    origin_message_id = context.bot_data.get('taboo_origin_message_id')

    card, _ = await get_card_async(code)
    name = _taboo_name(name_map, code) or (card.get('name') if card else code)
    restriction = _taboo_restriction_label(entry)
    text_note = entry.get('text') or entry.get('replacement_text') or ''
    img = None
    caption = None
    is_spoiler = False
    plain_text = None

    if card:
        caption, is_spoiler = _spoiler_caption(card)
        taboo_block = f"\n\n<b>Taboo:</b> {escape(restriction)}"
        if text_note:
            taboo_block += f"\n<i>{escape(text_note)}</i>"
        caption = caption + taboo_block
        image_src = card.get('imagesrc') or card.get('image_src')
        img = await _fetch_card_image(code, image_src)
    else:
        plain_text = f"<b>{escape(name)}</b> (<code>{code}</code>)\n<b>Taboo:</b> {escape(restriction)}"
        if text_note:
            plain_text += f"\n<i>{escape(text_note)}</i>"

    try:
        await query.message.delete()
    except Exception:
        pass

    if origin_chat_id and origin_message_id:
        reply_params = ReplyParameters(message_id=origin_message_id)
        if img:
            await update.get_bot().send_photo(
                chat_id=origin_chat_id,
                photo=img,
                caption=caption,
                parse_mode=ParseMode.HTML,
                has_spoiler=is_spoiler,
                reply_parameters=reply_params,
            )
        elif caption:
            await update.get_bot().send_message(
                chat_id=origin_chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_parameters=reply_params,
            )
        else:
            await update.get_bot().send_message(
                chat_id=origin_chat_id,
                text=plain_text or code,
                parse_mode=ParseMode.HTML,
                reply_parameters=reply_params,
            )


async def taboo_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Back to the selected taboo list's category screen."""
    query = update.callback_query
    await query.answer()
    taboo = context.bot_data.get('taboo_selected', {})
    cats = context.bot_data.get('taboo_cats', {})
    if not taboo:
        s = get_strings()
        await query.answer(s["taboo_session_expired"], show_alert=True)
        return
    text, markup = _taboo_detail_text_and_buttons(taboo, cats)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
