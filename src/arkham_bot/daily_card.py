import asyncio
import io
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape
from urllib.parse import urljoin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError

from .arkhamdb_client import download_image_sync, fetch_all_cards_sync
from .repositories.cards_repo import get_all_cards as _db_get_all_cards
from .card_provider import get_card
from .ai.daily_card_selector import choose_daily_card_with_ai, generate_card_commentary
from .config import (
    BASE_URL,
    EXTENSIONS_TO_TRY,
    POSTED_CARDS_FILE,
    POSTED_CARDS_LOCK,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    DAILY_POST_DAYS,
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
from .repositories.settings_repo import get_setting
from .repositories.history_repo import create_history_entry
from .text_formatters import format_card_back_caption, format_card_caption
from .i18n import get_strings


logger = logging.getLogger(__name__)

_WEEKDAY_CODES = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def _today_code(timezone_str: str) -> str:
    try:
        tz = ZoneInfo(timezone_str or 'UTC')
    except ZoneInfoNotFoundError:
        tz = ZoneInfo('UTC')
    return _WEEKDAY_CODES[datetime.now(tz).weekday()]


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


async def post_daily_card(specific_card_code=None, target_chat_id: str | None = None, is_scheduled: bool = False) -> DailyPostResult:
    """Posts the daily ArkhamDB card once. Never exits the process."""

    chat_id = str(target_chat_id or get_setting('telegram_chat_id', None) or TELEGRAM_CHAT_ID or "").strip()
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
            ai_language = get_setting('ai_language', 'pt-BR')
            ai_enabled = get_setting('ai_enabled', True)
            ai_auto_only = get_setting('ai_auto_only', True)
            ai_pre_message_delay = min(3600, max(0, int(get_setting('ai_pre_message_delay_seconds', 0) or 0)))
            ai_post_question_delay = min(3600, max(0, int(get_setting('ai_post_question_delay_seconds', 0) or 0)))
            ai_tone = get_setting('ai_tone', None) or None
            ai_pre_message_enabled = get_setting('ai_pre_message_enabled', True)
            ai_post_question_enabled = get_setting('ai_post_question_enabled', True)
            ai_model = get_setting('ai_model', None) or None
            ai_creativity = get_setting('ai_creativity', 'default')

            # When ai_auto_only=True, AI only runs for scheduled posts
            ai_allowed = ai_enabled and (is_scheduled or not ai_auto_only)

            from .config import AI_DAILY_CARD_ENABLED, GEMINI_API_KEY
            logger.info(
                f"AI config: enabled_db={ai_enabled} auto_only={ai_auto_only} "
                f"is_scheduled={is_scheduled} ai_allowed={ai_allowed} "
                f"has_key={bool(GEMINI_API_KEY)} model={ai_model or 'default'} "
                f"pre={ai_pre_message_enabled} post={ai_post_question_enabled}"
            )

            if specific_card_code:
                card, source = get_card(specific_card_code)
                if not card:
                    raise ValueError(f"Card not found: {specific_card_code}")
                card_code = specific_card_code
                logger.info(f"Specific Card selected from {source}: {card.get('name')} ({card_code}).")

                if ai_allowed:
                    ai_choice = await generate_card_commentary(
                        card, language=ai_language, tone=ai_tone,
                        pre_message_enabled=ai_pre_message_enabled,
                        post_question_enabled=ai_post_question_enabled,
                        model=ai_model, creativity=ai_creativity,
                    )
                    if ai_choice:
                        ai_pre_message = _telegram_html_text(ai_choice.pre_message)
                        ai_post_question = _telegram_html_text(ai_choice.post_question)
                        logger.info(f"AI commentary generated for manual post: {card_code}")
                    else:
                        logger.warning(f"AI commentary returned None for manual post: {card_code}")
                elif ai_enabled and ai_auto_only and not is_scheduled:
                    logger.info(f"AI skipped for manual post: ai_auto_only=True")
                else:
                    logger.info(f"AI skipped for manual post: ai_enabled=False")

            if card is None:
                all_cards = load_card_cache()

                if not all_cards:
                    logger.info("Card list cache empty. Fetching from DB...")
                    try:
                        all_cards = _db_get_all_cards()
                    except Exception as exc:
                        logger.warning(f"DB fetch failed, falling back to API: {exc}")
                        all_cards = fetch_all_cards_sync()
                    if all_cards:
                        save_card_cache(all_cards)

                include_spoilers = get_setting('include_spoilers', False)
                timezone_str = get_setting('timezone', 'America/Sao_Paulo')

                # Base pool: exclude meta types and spoilers
                valid_cards = [
                    c for c in all_cards
                    if c.get('type_code') not in ['set', 'campaign', 'scenario']
                    and (include_spoilers or not c.get('spoiler', False))
                ]

                # Per-day config is only applied when per-day mode is active.
                # If all weekdays are present in `daily_post_days`, global mode is active
                # and we must ignore per-day filters stored in `day_config`.
                day_config = get_setting('day_config', {})
                # Normalize configured post days
                post_days = get_setting('daily_post_days', DAILY_POST_DAYS)
                if isinstance(post_days, str):
                    post_days_list = [p.strip() for p in post_days.split(',') if p.strip()]
                elif isinstance(post_days, list):
                    post_days_list = post_days
                else:
                    post_days_list = []
                per_day_mode = set(post_days_list) != set(_WEEKDAY_CODES)

                today = _today_code(timezone_str)
                today_cfg = (
                    (day_config.get(today) or day_config.get('all'))
                    if isinstance(day_config, dict) and per_day_mode else None
                )

                # Pack/cycle filter from today's config
                today_packs = today_cfg.get('packs', []) if isinstance(today_cfg, dict) else []
                if isinstance(today_packs, list) and today_packs:
                    pack_filtered = [c for c in valid_cards if c.get('pack_code') in today_packs]
                    if pack_filtered:
                        valid_cards = pack_filtered
                        logger.info(f"Pack filter ({today}): {len(valid_cards)} cards in {len(today_packs)} packs.")
                    else:
                        logger.warning(f"No cards match pack filter for {today}. Ignoring.")

                unposted_cards = [c for c in valid_cards if c.get('code') not in posted_cards]

                if not unposted_cards:
                    logger.warning("All cards in current selection posted. Resetting cycle.")
                    await bot.send_message(
                        chat_id=chat_id,
                        text=get_strings()["daily_cycle_reset"],
                        parse_mode=ParseMode.HTML,
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

                # Card type filter from today's config (falls back to global allowed_card_types)
                today_types = today_cfg.get('types', []) if isinstance(today_cfg, dict) else []
                global_types = get_setting('allowed_card_types', None)
                types_to_apply = today_types if (isinstance(today_types, list) and today_types) else (
                    global_types if isinstance(global_types, list) and global_types else None
                )
                if types_to_apply:
                    type_filtered = [c for c in unposted_cards if c.get('type_code') in types_to_apply]
                    if type_filtered:
                        unposted_cards = type_filtered
                        logger.info(f"Type filter ({today}): {types_to_apply} → {len(unposted_cards)} cards.")
                    else:
                        logger.warning(f"No unposted cards match type filter for {today}: {types_to_apply}. Ignoring.")

                # AI selects card AND generates commentary in one call
                if not ai_allowed:
                    logger.info("AI skipped: ai_allowed=False — using random card selection")
                ai_choice = await choose_daily_card_with_ai(
                    unposted_cards, language=ai_language, tone=ai_tone,
                    pre_message_enabled=ai_pre_message_enabled,
                    post_question_enabled=ai_post_question_enabled,
                    model=ai_model, creativity=ai_creativity,
                ) if ai_allowed else None
                if ai_choice:
                    card = next((c for c in unposted_cards if c.get('code') == ai_choice.selected_card_code), None) or random.choice(unposted_cards)
                    ai_pre_message = _telegram_html_text(ai_choice.pre_message)
                    ai_post_question = _telegram_html_text(ai_choice.post_question)
                    logger.info(f"AI Card Selected: {card.get('name')} ({card.get('code')}). Reason: {ai_choice.reason}")
                else:
                    card = random.choice(unposted_cards)
                    if ai_allowed:
                        logger.warning(f"AI returned None for daily card — falling back to random.")
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
                    if ai_pre_message_delay > 0:
                        logger.info(f"Waiting {ai_pre_message_delay}s before posting card (ai_pre_message_delay)")
                        await asyncio.sleep(ai_pre_message_delay)

                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=card_image_bytes,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
                logger.info(f"Image (Front) for {card_code} posted successfully. Message ID: {message.message_id}")
                save_posted_card(card_code)
                log_posting_history(card_code, card.get('name'), "POSTED_FRONT_SUCCESS")
                try:
                    create_history_entry(
                        card_code=card_code,
                        card_name=card.get('name'),
                        status='POSTED_FRONT_SUCCESS',
                        source='scheduled' if is_scheduled else 'manual',
                        telegram_message_id=message.message_id,
                        target_chat_id=chat_id,
                    )
                except Exception as _he:
                    logger.warning(f"history_entry_failed: {_he}")
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

        if ai_post_question:
            try:
                if ai_post_question_delay > 0:
                    logger.info(f"Waiting {ai_post_question_delay}s before sending post question")
                    await asyncio.sleep(ai_post_question_delay)
                await bot.send_message(
                    chat_id=chat_id,
                    text=ai_post_question,
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=message.message_id,
                )
            except TelegramError as exc:
                logger.warning(f"Could not send AI discussion message: {exc}")

        logger.info(f"Card {card_code} processed successfully. Finalizing execution.")
        return DailyPostResult(True, card_code=card_code, card_name=card.get('name'), message_id=message.message_id)

    error = "Failed to post a card after all retry attempts."
    logger.critical(error)
    return DailyPostResult(False, error=error)
