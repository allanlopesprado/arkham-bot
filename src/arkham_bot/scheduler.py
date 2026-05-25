import asyncio
import json
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .config import (
    BOT_COMMANDS_POLLING_ENABLED,
    DAILY_POST_DAYS,
    DAILY_POST_ENABLED,
    DAILY_POST_TIMES,
    DAILY_SCHEDULER_STATE_FILE,
    TIMEZONE,
)
from .daily_card import post_daily_card
from .repositories.settings_repo import get_setting


logger = logging.getLogger(__name__)
WEEKDAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
POST_WINDOW_MINUTES = 10


def _load_state() -> dict:
    if not DAILY_SCHEDULER_STATE_FILE.exists():
        return {}
    try:
        return json.loads(DAILY_SCHEDULER_STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"scheduler_tick_error: failed to load state: {exc}")
        return {}


def _save_state(state: dict) -> None:
    DAILY_SCHEDULER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DAILY_SCHEDULER_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_due(now: datetime, post_time: str, state: dict) -> bool:
    try:
        hour, minute = [int(part) for part in post_time.split(":", 1)]
        scheduled = datetime.combine(now.date(), time(hour, minute), tzinfo=now.tzinfo)
    except ValueError:
        logger.warning(f"scheduler_tick_error: invalid time configured: {post_time}")
        return False
    elapsed_minutes = (now - scheduled).total_seconds() / 60
    if elapsed_minutes < 0 or elapsed_minutes > POST_WINDOW_MINUTES:
        return False
    return state.get("last_daily_post_date") != now.date().isoformat() or state.get("last_daily_post_time") != post_time


def _as_list(value, default: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return default


def _runtime_config():
    enabled = bool(get_setting("daily_post_enabled", DAILY_POST_ENABLED))
    post_times = _as_list(get_setting("daily_post_times", DAILY_POST_TIMES), DAILY_POST_TIMES)
    post_days = _as_list(get_setting("daily_post_days", DAILY_POST_DAYS), DAILY_POST_DAYS)
    timezone_name = str(get_setting("timezone", TIMEZONE) or TIMEZONE)
    return enabled, post_times, post_days, timezone_name


async def daily_scheduler_loop() -> None:
    logger.info("scheduler_started")
    while True:
        try:
            daily_post_enabled, daily_post_times, daily_post_days, timezone_name = _runtime_config()
            timezone = ZoneInfo(timezone_name)
            if daily_post_enabled:
                now = datetime.now(timezone)
                state = _load_state()
                for post_time in daily_post_times:
                    if WEEKDAY_CODES[now.weekday()] not in daily_post_days:
                        continue
                    if _is_due(now, post_time, state):
                        logger.info("daily_post_due")
                        result = await post_daily_card()
                        state = {
                            "last_daily_post_date": now.date().isoformat(),
                            "last_daily_post_time": post_time,
                            "last_daily_post_status": "success" if result.success else "failed",
                            "last_daily_post_error": result.error,
                            "last_daily_post_card_code": result.card_code,
                            "last_daily_post_message_id": result.message_id,
                        }
                        _save_state(state)
                        if result.success:
                            logger.info("daily_post_success")
                        else:
                            logger.error(f"daily_post_failure: {result.error}")
                    else:
                        logger.debug("daily_post_skipped_not_due")
        except asyncio.CancelledError:
            logger.info("scheduler_stopped")
            raise
        except Exception as exc:
            logger.exception(f"scheduler_tick_error: {exc}")
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("scheduler_stopped")
            raise


def start_daily_scheduler(application) -> None:
    application.create_task(daily_scheduler_loop(), name="daily-card-scheduler")
    if BOT_COMMANDS_POLLING_ENABLED:
        try:
            from .bot_commands_worker import start_bot_commands_worker

            start_bot_commands_worker(application)
        except Exception as exc:
            logger.warning(f"bot_commands_worker_not_started: {exc}")
