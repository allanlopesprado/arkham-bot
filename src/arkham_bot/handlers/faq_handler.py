import io
import logging
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
from ..services.card_provider import get_card_async
from .common import (
    _arkhamdb_html_to_telegram,
    _check_rate_limit,
    _chunks,
    _fetch_faq,
)

logger = logging.getLogger(__name__)


async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_rate_limit(update):
        return
    s = get_strings()
    if not context.args:
        await update.message.reply_text(s["faq_usage"])
        return
    card_code = context.args[0].strip()
    user_reply = ReplyParameters(message_id=update.message.message_id)
    try:
        faq = await _fetch_faq(card_code)
        if not faq:
            await update.message.reply_text(
                s["faq_not_found"].format(card_code=escape(card_code)),
                parse_mode=ParseMode.HTML,
                reply_parameters=user_reply,
            )
            return

        entries = faq if isinstance(faq, list) else [faq]
        parts = []
        for i, entry in enumerate(entries):
            if i > 0:
                parts.append("─────────────")
            if isinstance(entry, dict):
                raw_html = str(entry.get('html') or entry.get('text') or '').strip()
                if raw_html:
                    parts.append(_arkhamdb_html_to_telegram(raw_html))
            else:
                parts.append(_arkhamdb_html_to_telegram(str(entry)))
        faq_text = "\n\n".join(parts)

        last_updated = None
        for entry in reversed(entries):
            if isinstance(entry, dict):
                upd = entry.get('updated') or {}
                date_str = upd.get('date', '') if isinstance(upd, dict) else ''
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.split('.')[0])
                        last_updated = dt.strftime('%d/%m/%Y')
                    except Exception:
                        pass
                    break

        if last_updated:
            faq_text += f"\n\n🕐 <i>{s.get('faq_last_updated', 'Atualizado em')} {last_updated}</i>"
        faq_text += "\n" + s["fmt_view_arkhamdb"].format(code=escape(card_code))

        img_bytes = None
        try:
            card_data, _ = await get_card_async(card_code)
            if card_data:
                image_src = card_data.get('imagesrc')
                for ext in EXTENSIONS_TO_TRY:
                    img_path = image_src if image_src and image_src.lower().endswith(ext) else f"/bundles/cards/{card_code}{ext}"
                    try:
                        content = await download_image_async(urljoin(BASE_URL, img_path))
                        buf = io.BytesIO(content)
                        Image.open(buf).verify()
                        buf.seek(0)
                        img_bytes = buf
                        break
                    except Exception:
                        continue
        except Exception:
            pass

        if img_bytes:
            photo_msg = await update.message.reply_photo(
                photo=img_bytes,
                reply_parameters=user_reply,
            )
        else:
            photo_msg = None

        anchor_id = photo_msg.message_id if photo_msg else update.message.message_id
        chunks = _chunks(faq_text, 3900)
        last_id = anchor_id
        for chunk in chunks:
            sent = await update.message.get_bot().send_message(
                chat_id=update.effective_chat.id,
                text=chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_parameters=ReplyParameters(message_id=last_id),
            )
            last_id = sent.message_id

    except Exception as exc:
        logger.error(f"faq_command_failed: {exc}", exc_info=True)
        await update.message.reply_text(s["faq_error"])
