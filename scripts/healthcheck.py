import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from arkham_bot.config import (
    SUPABASE_ENABLED,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ensure_runtime_dirs,
)
from arkham_bot.logging_config import setup_logging
from arkham_bot.supabase_client import get_supabase_client


logger = setup_logging()


async def _check_telegram(strict: bool) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        msg = "Telegram env vars missing."
        if strict:
            logger.error(msg)
            return False
        logger.warning(msg)
        return True
    try:
        from telegram import Bot

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        me = await bot.get_me()
        logger.info("telegram_get_me_ok: @%s", me.username)
        return True
    except Exception as exc:
        logger.error("telegram_check_failed: %s", exc)
        return not strict


def _check_supabase(strict: bool) -> bool:
    if not SUPABASE_ENABLED:
        msg = "Supabase env vars missing; Supabase checks skipped."
        if strict:
            logger.error(msg)
            return False
        logger.warning(msg)
        return True
    try:
        client = get_supabase_client()
        client.get("bot_settings", {"limit": "1"})
        logger.info("supabase_rest_ok")
        return True
    except Exception as exc:
        logger.error("supabase_check_failed: %s", exc)
        return not strict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Fail when Telegram/Supabase checks cannot run.")
    args = parser.parse_args(argv)

    ensure_runtime_dirs()
    checks = [
        asyncio.run(_check_telegram(args.strict)),
        _check_supabase(args.strict),
    ]
    if all(checks):
        logger.info("healthcheck_ok")
        return 0
    logger.error("healthcheck_failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
