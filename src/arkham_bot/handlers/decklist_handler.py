import io
import logging
import re
from datetime import datetime
from html import escape
from urllib.parse import urljoin

from PIL import Image
from telegram import ReplyParameters, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..clients.arkhamdb_client import download_image_async
from ..core.config import BASE_URL, EXTENSIONS_TO_TRY
from ..i18n import get_strings
from .common import (
    _check_rate_limit,
    _chunks,
    _fetch_all_cards,
    _fetch_decklist_cached,
)

logger = logging.getLogger(__name__)


async def decklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    s = get_strings()
    if not context.args:
        await update.message.reply_text(s["decklist_usage"])
        return

    raw_arg = context.args[0].strip()
    match = re.search(r"(\d+)", raw_arg)
    if not match:
        await update.message.reply_text(s["decklist_invalid_id"])
        return

    decklist_id = match.group(1)
    user_reply = ReplyParameters(message_id=update.message.message_id)
    try:
        deck = await _fetch_decklist_cached(decklist_id)
        name = escape(deck.get('name') or s["decklist_untitled"])
        inv_name = escape(deck.get('investigator_name') or deck.get('investigator_code') or s["decklist_unknown_investigator"])
        inv_code = deck.get('investigator_code', '')
        slots: dict = deck.get('slots') if isinstance(deck.get('slots'), dict) else {}
        xp = deck.get('xp') or 0
        taboo_id = deck.get('taboo_id')
        date_upd = deck.get('date_update', '')
        description = (deck.get('description_md') or '').strip()
        version = deck.get('version') or '1.0'

        date_str = ''
        if date_upd:
            try:
                dt = datetime.fromisoformat(date_upd.replace('Z', '+00:00'))
                date_str = dt.strftime('%d/%m/%Y')
            except Exception:
                pass

        all_cards = await _fetch_all_cards(include_encounter=True)
        card_map = {c['code']: c for c in all_cards if c.get('code')}

        TYPE_ORDER = ['investigator', 'asset', 'event', 'skill', 'enemy', 'treachery', 'location']
        grouped: dict[str, list[str]] = {}
        type_labels: dict[str, str] = {}
        total_cards = 0
        for code, qty in sorted(slots.items()):
            card = card_map.get(code)
            cname = escape(card['name'] if card else code)
            ctype = (card.get('type_code') or 'other') if card else 'other'
            if card and card.get('type_name') and ctype not in type_labels:
                type_labels[ctype] = card['type_name']
            link = f"<a href='https://arkhamdb.com/card/{code}'>{cname}</a>"
            prefix = f"×{qty} · "
            grouped.setdefault(ctype, []).append(f"{prefix}{link}")
            total_cards += qty

        card_lines = []
        for t in TYPE_ORDER:
            if t in grouped and t != 'investigator':
                tname = escape(type_labels.get(t, t.capitalize()))
                card_lines.append(f"\n▪️ <b>{tname}</b>")
                card_lines.extend(f"  {item}" for item in grouped[t])
        for t, items in grouped.items():
            if t not in TYPE_ORDER and t != 'investigator':
                tname = escape(type_labels.get(t, t.capitalize()))
                card_lines.append(f"\n▪️ <b>{tname}</b>")
                card_lines.extend(f"  {item}" for item in items)

        caption_lines = [
            f"🃏 <b>{name}</b>",
            f"🔵 {inv_name}",
        ]
        if date_str:
            caption_lines.append(f"📅 {s.get('decklist_updated', 'Atualizado em')} {date_str}")
        caption_lines.append(f"📦 {total_cards} {s.get('decklist_cards_label', 'cartas')} · v{version}")
        if xp:
            caption_lines.append(f"⭐ XP: {xp}")
        if taboo_id:
            caption_lines.append(f"🚫 {s.get('decklist_taboo_active', 'Com taboo')}")
        if description:
            clean_desc = re.sub(r'<[^>]+>', '', description)
            clean_desc = re.sub(r'^#+\s*', '', clean_desc, flags=re.MULTILINE)
            clean_desc = re.sub(r'^>\s*', '', clean_desc, flags=re.MULTILINE)
            clean_desc = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', clean_desc)
            clean_desc = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean_desc)
            clean_desc = re.sub(r'\n{3,}', '\n\n', clean_desc).strip()
            if clean_desc:
                truncated = clean_desc[:300] + ("…" if len(clean_desc) > 300 else "")
                caption_lines.append(f"\n<i>{escape(truncated)}</i>")
        caption_lines.append(f"\n🔗 <a href='https://arkhamdb.com/decklist/view/{decklist_id}'>{s.get('decklist_view_label', 'Ver no ArkhamDB')}</a>")
        caption = "\n".join(caption_lines)

        inv_img = None
        if inv_code:
            inv_card = card_map.get(inv_code)
            if inv_card:
                image_src = inv_card.get('imagesrc')
                for ext in EXTENSIONS_TO_TRY:
                    img_path = image_src if image_src and image_src.lower().endswith(ext) else f"/bundles/cards/{inv_code}{ext}"
                    try:
                        content = await download_image_async(urljoin(BASE_URL, img_path))
                        buf = io.BytesIO(content)
                        Image.open(buf).verify()
                        buf.seek(0)
                        inv_img = buf
                        break
                    except Exception:
                        continue

        if inv_img:
            deck_msg = await update.message.reply_photo(
                photo=inv_img, caption=caption, parse_mode=ParseMode.HTML,
                reply_parameters=user_reply,
            )
        else:
            deck_msg = await update.message.reply_text(
                caption, parse_mode=ParseMode.HTML,
                reply_parameters=user_reply,
                disable_web_page_preview=True,
            )

        if card_lines:
            cards_text = f"<b>{s.get('decklist_cards_title', 'Cartas do deck')}</b>" + "\n".join(card_lines)
            for chunk in _chunks(cards_text, 3900):
                deck_msg = await update.message.get_bot().send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    reply_parameters=ReplyParameters(message_id=deck_msg.message_id),
                )

    except Exception as exc:
        logger.error(f"decklist_command_failed: {exc}", exc_info=True)
        await update.message.reply_text(s["decklist_error"])
