import asyncio
import io
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape
from urllib.parse import urljoin

from PIL import Image
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError

from .arkhamdb_client import download_image_sync, fetch_all_cards_sync
from .card_provider import get_card
from .ai.daily_card_selector import choose_daily_card_with_ai
from .config import (
    BASE_URL,
    EXTENSIONS_TO_TRY,
    POSTED_CARDS_FILE,
    POSTED_CARDS_LOCK,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from .local_storage import (
    load_card_cache,
    load_last_pinned_daily_card,
    load_posted_cards,
    log_error_to_file,
    log_posting_history,
    safe_atomic_write,
    save_card_cache,
    save_last_pinned_daily_card,
    save_posted_card,
)
from .text_formatters import format_card_back_caption, format_card_caption


logger = logging.getLogger(__name__)
DEFAULT_DISCUSSION_MESSAGE = "Investigators, ready for another revealed mystery? The Card of the Day is on the table!"


def _telegram_html_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return escape(text) if text else None


@dataclass(slots=True)
class DailyPostResult:
    success: bool
    card_code: str | None = None
    card_name: str | None = None
    message_id: int | None = None
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


async def _unpin_previous_daily_card(bot: Bot) -> None:
    previous = load_last_pinned_daily_card()
    if not previous:
        return
    chat_id = previous.get("chat_id")
    message_id = previous.get("message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Previous daily card unpinned. chat_id={chat_id} message_id={message_id}")
    except TelegramError as exc:
        logger.warning(f"Could not unpin previous daily card {message_id}: {exc}")


async def _pin_new_daily_card(bot: Bot, chat_id: str, card_code: str, message_id: int) -> None:
    try:
        await _unpin_previous_daily_card(bot)
        await bot.pin_chat_message(chat_id=chat_id, message_id=message_id, disable_notification=True)
        save_last_pinned_daily_card({
            "chat_id": chat_id,
            "message_id": message_id,
            "card_code": card_code,
            "posted_date": datetime.now().date().isoformat(),
            "created_at": datetime.now().astimezone().isoformat(),
        })
    except TelegramError as exc:
        logger.warning(f"Could not pin message {card_code}: {exc}")
    except Exception as exc:
        logger.warning(f"Could not persist pin state for {card_code}: {exc}", exc_info=True)


async def post_daily_card(specific_card_code=None, target_chat_id: str | None = None) -> DailyPostResult:
    """Posts the daily ArkhamDB card once. Never exits the process."""

    chat_id = str(target_chat_id or TELEGRAM_CHAT_ID or "").strip()
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        error = "Telegram token or chat id not configured."
        logger.error(error)
        return DailyPostResult(success=False, error=error)

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    posted_cards = load_posted_cards()
    max_card_attempts = 5

    while max_card_attempts > 0:
        card = None
        card_code = None
        card_image_bytes = None
        ai_pre_message = None
        ai_post_question = None

        try:
            if specific_card_code:
                card, source = get_card(specific_card_code)
                if not card:
                    raise ValueError(f"Card not found: {specific_card_code}")
                card_code = specific_card_code
                logger.info(f"Specific Card selected from {source}: {card.get('name')} ({card_code}).")

            if card is None or (specific_card_code and card.get('code') != specific_card_code):
                all_cards = load_card_cache()

                if not all_cards:
                    logger.info("Card list cache expired or missing. Fetching from ArkhamDB API...")
                    all_cards = fetch_all_cards_sync()
                    save_card_cache(all_cards)

                valid_cards = [
                    c for c in all_cards
                    if c.get('type_code') not in ['set', 'campaign', 'scenario']
                    and c.get('spoiler', False) is False
                ]

                unposted_cards = [c for c in valid_cards if c.get('code') not in posted_cards]

                if not unposted_cards:
                    logger.warning("All cards posted. Resetting cycle and file.")
                    await bot.send_message(
                        chat_id=chat_id,
                        text="🚨 **POSTING CYCLE RESET** 🚨\nAll non-spoiler cards have been posted.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    posted_cards.clear()
                    try:
                        safe_atomic_write("", POSTED_CARDS_FILE, POSTED_CARDS_LOCK, data_type='text')
                    except Exception:
                        pass
                    log_posting_history("N/A", "Cycle Reset", "SUCCESS")
                    unposted_cards = valid_cards
                    if not unposted_cards:
                        raise RuntimeError("No valid cards found after reset.")

                ai_choice = await choose_daily_card_with_ai(unposted_cards)
                if ai_choice:
                    card = next((candidate for candidate in unposted_cards if candidate.get('code') == ai_choice.selected_card_code), None) or random.choice(unposted_cards)
                    ai_pre_message = _telegram_html_text(ai_choice.pre_message)
                    ai_post_question = _telegram_html_text(ai_choice.post_question)
                    logger.info(f"AI Card Selected: {card.get('name')} ({card.get('code')}). Reason: {ai_choice.reason}")
                else:
                    card = random.choice(unposted_cards)
                    logger.info(f"Random Card Selected: {card.get('name')} ({card.get('code')}).")
                card_code = card.get('code')

        except Exception as exc:
            logger.error(f"Failed to fetch or process card list (via retry): {exc}", exc_info=True)
            max_card_attempts -= 1
            await asyncio.sleep(2)
            continue

        if card_code is None or card is None:
            max_card_attempts -= 1
            continue

        image_src = card.get('imagesrc')
        found_image = False

        for ext in EXTENSIONS_TO_TRY:
            if image_src and image_src.lower().endswith(ext):
                card_image_path = image_src
            else:
                card_image_path = f"/bundles/cards/{card_code}{ext}"

            card_image_url = urljoin(BASE_URL, card_image_path)

            try:
                image_content = download_image_sync(card_image_url)
                card_image_bytes = io.BytesIO(image_content)
                Image.open(card_image_bytes).verify()
                card_image_bytes.seek(0)
                found_image = True
                logger.info(f"Front image successfully downloaded from URL: {card_image_url}")
                break
            except Exception:
                continue

        if not found_image:
            logger.error(f"Critical Failure: Could not download front image for {card_code} after all attempts.")
            log_posting_history(card_code, card.get('name'), "FAILED_DOWNLOAD")
            log_error_to_file("Front Image Download", "Failed to download card image after all attempts.", card_code)
            max_card_attempts -= 1
            continue

        message = None
        telegram_attempts = 3
        pre_message_sent = False

        while telegram_attempts > 0:
            try:
                caption = format_card_caption(card, is_interactive=False)
                card_image_bytes.seek(0)

                if ai_pre_message and not pre_message_sent:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=ai_pre_message,
                        parse_mode=ParseMode.HTML,
                    )
                    pre_message_sent = True

                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=card_image_bytes,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
                logger.info(f"Image (Front) for {card_code} posted successfully. Message ID: {message.message_id}")
                save_posted_card(card_code)
                log_posting_history(card_code, card.get('name'), "POSTED_FRONT_SUCCESS")
                break

            except RetryAfter as exc:
                retry_after = exc.retry_after if exc.retry_after > 0 else 5
                logger.warning(f"Telegram Flood control: Retrying after {retry_after}s.")
                await asyncio.sleep(retry_after)
                telegram_attempts -= 1

            except Exception as exc:
                logger.error(f"CRITICAL: Final failure to post card {card_code} after retries: {exc}", exc_info=True)
                telegram_attempts -= 1
                await asyncio.sleep(5)

        if message is None:
            max_card_attempts -= 1
            continue

        if card.get('double_sided') is True and message:
            back_image_src = card.get('backimagesrc')
            back_text_raw = card.get('back_text')
            back_flavor_raw = card.get('back_flavor')

            if back_text_raw or back_flavor_raw:
                back_image_bytes = None
                found_back_image = False

                if back_image_src:
                    for ext in EXTENSIONS_TO_TRY:
                        back_image_path = back_image_src or f"/bundles/cards/{card_code}b{ext}"
                        back_image_url = urljoin(BASE_URL, back_image_path)

                        try:
                            back_image_content = download_image_sync(back_image_url)
                            back_image_bytes = io.BytesIO(back_image_content)
                            Image.open(back_image_bytes).verify()
                            back_image_bytes.seek(0)
                            found_back_image = True
                            break
                        except Exception:
                            continue

                back_caption = format_card_back_caption(card, back_text_raw, is_interactive=False)

                if found_back_image:
                    try:
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=back_image_bytes,
                            caption=back_caption,
                            parse_mode=ParseMode.HTML,
                            reply_to_message_id=message.message_id,
                        )
                        log_posting_history(card_code, card.get('name'), "POSTED_BACK")
                    except Exception as exc:
                        logger.error(f"Failed to post back image: {exc}. Trying as text.")
                        found_back_image = False

                if not found_back_image:
                    if "🔗" in back_caption:
                        back_caption = re.sub(r"\n+🔗 <a href='[^']+'>View on ArkhamDB</a>$", "", back_caption)
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=back_caption,
                            parse_mode=ParseMode.HTML,
                            reply_to_message_id=message.message_id,
                        )
                        log_posting_history(card_code, card.get('name'), "POSTED_BACK_TEXT_ONLY")
                    except TelegramError as exc:
                        logger.error(f"Failed to send back side as text: {exc}")

        await _pin_new_daily_card(bot, chat_id, card_code, message.message_id)

        try:
            discussion_message = ai_post_question or _telegram_html_text(DEFAULT_DISCUSSION_MESSAGE)
            await bot.send_message(
                chat_id=chat_id,
                text=discussion_message,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=message.message_id,
            )
        except TelegramError as exc:
            logger.warning(f"Could not send discussion message: {exc}")

        logger.info(f"Card {card_code} processed successfully. Finalizing execution.")
        return DailyPostResult(True, card_code=card_code, card_name=card.get('name'), message_id=message.message_id)

    error = "Failed to post a card after all retry attempts."
    logger.critical(error)
    return DailyPostResult(False, error=error)
