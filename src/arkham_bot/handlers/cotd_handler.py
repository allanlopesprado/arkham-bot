import asyncio
import logging
from datetime import datetime
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..i18n import get_strings
from .common import _check_rate_limit

logger = logging.getLogger(__name__)


def _months() -> list[str]:
    return get_strings()["months"]


def _cotd_fetch_years() -> list[int]:
    from ..core.supabase_client import get_supabase_client
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get('bot_posting_history', {
        'select': 'created_at',
        'source': 'eq.scheduled',
        'order': 'created_at.asc',
        'limit': '5000',
    })
    years = sorted({datetime.fromisoformat(r['created_at']).year for r in rows if r.get('created_at')})
    return years


def _cotd_fetch_months(year: int) -> list[int]:
    from ..core.supabase_client import get_supabase_client
    client = get_supabase_client()
    if not client:
        return []
    rows = client.get('bot_posting_history', [
        ('select', 'created_at'),
        ('source', 'eq.scheduled'),
        ('created_at', f'gte.{year}-01-01T00:00:00Z'),
        ('created_at', f'lt.{year + 1}-01-01T00:00:00Z'),
        ('order', 'created_at.asc'),
        ('limit', '500'),
    ])
    months = sorted({datetime.fromisoformat(r['created_at']).month for r in rows if r.get('created_at')})
    return months


def _cotd_fetch_cards(year: int, month: int, tz_name: str = 'America/Sao_Paulo') -> list[dict]:
    from zoneinfo import ZoneInfo
    from ..core.supabase_client import get_supabase_client
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
    s = get_strings()
    years = await asyncio.to_thread(_cotd_fetch_years)
    if not years:
        await update.message.reply_text(s["cotd_no_cards"])
        return
    buttons = [[InlineKeyboardButton(str(y), callback_data=f"COTD_YEAR_{y}")] for y in years]
    await update.message.reply_text(
        s["cotd_select_year"],
        reply_markup=InlineKeyboardMarkup(buttons),
        reply_parameters=ReplyParameters(message_id=update.message.message_id),
    )


async def cotd_year_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        year = int(query.data.split('_')[-1])
    except (ValueError, IndexError):
        await query.edit_message_text(get_strings()["taboo_session_expired"])
        return
    s = get_strings()
    months = await asyncio.to_thread(_cotd_fetch_months, year)
    if not months:
        await query.edit_message_text(s["cotd_no_year"])
        return
    month_names = _months()
    rows = [months[i:i+4] for i in range(0, len(months), 4)]
    buttons = [
        [InlineKeyboardButton(month_names[m - 1], callback_data=f"COTD_MONTH_{year}_{m}") for m in row]
        for row in rows
    ]
    buttons.append([InlineKeyboardButton(s["cotd_btn_back"], callback_data="COTD_BACK")])
    await query.edit_message_text(s["cotd_select_month"].format(year=year), reply_markup=InlineKeyboardMarkup(buttons))


async def cotd_month_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        year_str, month_str = query.data.replace('COTD_MONTH_', '').split('_')
        year, month = int(year_str), int(month_str)
    except (ValueError, IndexError):
        await query.edit_message_text(get_strings()["taboo_session_expired"])
        return
    s = get_strings()
    cards = await asyncio.to_thread(_cotd_fetch_cards, year, month)
    if not cards:
        await query.edit_message_text(s["cotd_no_month"])
        return
    month_name = _months()[month - 1]
    lines = [s["cotd_month_title"].format(month_name=month_name, year=year), ""]
    for c in cards:
        name = escape(c['name'] or c['code'])
        url = f"https://arkhamdb.com/card/{c['code']}"
        lines.append(f"{c['day']:02d}/{month:02d} - <a href='{url}'>{name}</a>")
    text = "\n".join(lines)
    from telegram import LinkPreviewOptions
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))


async def cotd_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    s = get_strings()
    years = await asyncio.to_thread(_cotd_fetch_years)
    buttons = [[InlineKeyboardButton(str(y), callback_data=f"COTD_YEAR_{y}")] for y in years]
    await query.edit_message_text(s["cotd_select_year"], reply_markup=InlineKeyboardMarkup(buttons))
