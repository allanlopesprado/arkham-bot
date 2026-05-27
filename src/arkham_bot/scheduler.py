import asyncio
import json
import logging
from datetime import datetime, time, timedelta
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
from .repositories.commands_repo import enqueue_command


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


def _slot_key(date_iso: str, post_time: str) -> str:
    return f"{date_iso}_{post_time}"


def _is_due(now: datetime, post_time: str, state: dict, before_seconds: int = 0) -> bool:
    try:
        hour, minute = [int(part) for part in post_time.split(":", 1)]
        scheduled = datetime.combine(now.date(), time(hour, minute), tzinfo=now.tzinfo)
        if before_seconds and isinstance(before_seconds, int) and before_seconds > 0:
            scheduled = scheduled - timedelta(seconds=before_seconds)
    except ValueError:
        logger.warning(f"scheduler_tick_error: invalid time configured: {post_time}")
        return False
    elapsed_minutes = (now - scheduled).total_seconds() / 60
    if elapsed_minutes < 0 or elapsed_minutes > POST_WINDOW_MINUTES:
        return False
    posted_slots = state.get("posted_slots", [])
    return _slot_key(now.date().isoformat(), post_time) not in posted_slots


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
    day_config = get_setting("day_config", {})
    timezone_name = str(get_setting("timezone", TIMEZONE) or TIMEZONE)
    return enabled, post_times, post_days, timezone_name, day_config


def _sync_config():
    enabled = bool(get_setting("sync_schedule_enabled", False))
    days = _as_list(get_setting("sync_schedule_days", ["sun"]), ["sun"])
    time_str = str(get_setting("sync_schedule_time", "03:00") or "03:00")
    return enabled, days, time_str


def _is_sync_due(now: datetime, sync_time: str, state: dict) -> bool:
    try:
        hour, minute = [int(p) for p in sync_time.split(":", 1)]
        scheduled = datetime.combine(now.date(), time(hour, minute), tzinfo=now.tzinfo)
    except ValueError:
        return False
    elapsed_minutes = (now - scheduled).total_seconds() / 60
    if elapsed_minutes < 0 or elapsed_minutes > POST_WINDOW_MINUTES:
        return False
    return state.get("last_sync_date") != now.date().isoformat()


def _times_for_day(day_code: str, default_times: list[str], day_config, post_days=None) -> list[str]:
    # If all weekdays are configured in post_days, global mode is active — use default_times
    if post_days is None:
        # preserve original behavior when post_days not provided
        pass
    else:
        try:
            if isinstance(post_days, list) and set(post_days) == set(WEEKDAY_CODES):
                return default_times
            if isinstance(post_days, str):
                post_days_list = [d.strip() for d in post_days.split(',') if d.strip()]
                if set(post_days_list) == set(WEEKDAY_CODES):
                    return default_times
        except Exception:
            # Fall back to per-day behavior on unexpected value
            pass

    if not isinstance(day_config, dict):
        return default_times
    cfg = day_config.get(day_code)
    if not isinstance(cfg, dict) or "times" not in cfg:
        return default_times
    return _as_list(cfg.get("times"), [])


async def daily_scheduler_loop() -> None:
    logger.info("scheduler_started")
    while True:
        try:
            daily_post_enabled, daily_post_times, daily_post_days, timezone_name, day_config = _runtime_config()
            timezone = ZoneInfo(timezone_name)
            now = datetime.now(timezone)
            state = _load_state()
            today = WEEKDAY_CODES[now.weekday()]

            if daily_post_enabled:
                # Determine whether we should trigger earlier to allow AI pre-message delays
                ai_enabled = bool(get_setting('ai_enabled', True))
                ai_pre_enabled = bool(get_setting('ai_pre_message_enabled', True))
                try:
                    ai_pre_delay = max(0, int(get_setting('ai_pre_message_delay_seconds', 0) or 0))
                except Exception:
                    ai_pre_delay = 0
                before_seconds = ai_pre_delay if (ai_enabled and ai_pre_enabled and ai_pre_delay > 0) else 0

                for post_time in _times_for_day(today, daily_post_times, day_config, daily_post_days):
                    if today not in daily_post_days:
                        continue
                    if _is_due(now, post_time, state, before_seconds=before_seconds):
                        logger.info("daily_post_due")
                        result = await post_daily_card(is_scheduled=True)
                        today_iso = now.date().isoformat()
                        # Keep only slots from today to avoid unbounded growth
                        posted_slots = [s for s in state.get("posted_slots", []) if s.startswith(today_iso)]
                        posted_slots.append(_slot_key(today_iso, post_time))
                        state.update({
                            "posted_slots": posted_slots,
                            "last_daily_post_date": today_iso,
                            "last_daily_post_time": post_time,
                            "last_daily_post_status": "success" if result.success else "failed",
                            "last_daily_post_error": result.error,
                            "last_daily_post_card_code": result.card_code,
                            "last_daily_post_message_id": result.message_id,
                        })
                        _save_state(state)
                        if result.success:
                            logger.info("daily_post_success")
                        else:
                            logger.error(f"daily_post_failure: {result.error}")
                    else:
                        logger.debug("daily_post_skipped_not_due")

            # Auto sync
            sync_enabled, sync_days, sync_time_str = _sync_config()
            if sync_enabled:
                today = WEEKDAY_CODES[now.weekday()]
                if today in sync_days and _is_sync_due(now, sync_time_str, state):
                    logger.info("auto_sync_due: enqueuing sync_arkhamdb")
                    try:
                        enqueue_command("sync_arkhamdb", {"sync_faq": False, "source": "scheduler"})
                        state["last_sync_date"] = now.date().isoformat()
                        _save_state(state)
                        logger.info("auto_sync_enqueued")
                    except Exception as sync_exc:
                        logger.error(f"auto_sync_enqueue_failed: {sync_exc}")

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
