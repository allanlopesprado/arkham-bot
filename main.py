import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import filelock

from arkham_bot.core.config import (
    CACHE_FILE,
    CACHE_LOCK,
    HISTORY_FILE,
    MAIN_PROCESS_LOCK,
    POSTED_CARDS_FILE,
    POSTED_CARDS_LOCK,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ensure_runtime_dirs,
)
from arkham_bot.core.logging_config import setup_logging


logger = setup_logging()


async def interactive_post_init(application):
    from telegram import BotCommand
    from arkham_bot.services.scheduler import start_daily_scheduler
    from arkham_bot.handlers.telegram_handlers import bot_started_message
    from arkham_bot.services.heartbeat import start_heartbeat
    from arkham_bot.core.supabase_client import get_supabase_client

    await application.bot.set_my_commands([
        BotCommand("search",    "Busca cartas por nome"),
        BotCommand("card",      "Busca carta por código"),
        BotCommand("sets",      "Navega cartas por set/expansão"),
        BotCommand("taboo",     "Lista taboo"),
        BotCommand("faq",       "FAQ de uma carta (ex: /faq 01001)"),
        BotCommand("decklist",  "Decklist do ArkhamDB (ex: /decklist 12345)"),
        BotCommand("cotd",      "Histórico de cartas do dia"),
        BotCommand("status",    "Status do bot"),
    ])
    await bot_started_message(application)
    await start_daily_scheduler(application)
    supabase = get_supabase_client()
    if supabase:
        await start_heartbeat(supabase)


def run_interactive_bot():
    """Runs the bot in Long Polling mode using ApplicationBuilder."""
    from telegram.ext import ApplicationBuilder
    from arkham_bot.handlers.telegram_handlers import register_handlers

    logger.info("--- STARTING INTERACTIVE MODE (LONG POLLING) ---")

    if not TELEGRAM_BOT_TOKEN:
        logger.critical("Telegram token not configured for interactive mode.")
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")

    from arkham_bot.services.scheduler import stop_daily_scheduler
    from arkham_bot.services.heartbeat import stop_heartbeat

    async def on_shutdown(app):
        await stop_daily_scheduler(app)
        await stop_heartbeat(app)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(interactive_post_init).post_shutdown(on_shutdown).build()
    register_handlers(application)

    logger.info("Starting polling...")
    application.run_polling()


def bootstrap_check(require_telegram: bool = True) -> bool:
    """Performs local integrity checks."""
    logger.info("--- BOOTSTRAP CHECK STARTED ---")
    ensure_runtime_dirs()

    if require_telegram and not TELEGRAM_BOT_TOKEN:
        logger.critical("CRITICAL ERROR: Telegram token not configured.")
        return False
    if require_telegram and not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set in .env — will use telegram_chat_id from bot settings.")

    file_lock_pairs = [
        (POSTED_CARDS_FILE, POSTED_CARDS_LOCK),
        (HISTORY_FILE, HISTORY_FILE.with_suffix(".lock")),
        (CACHE_FILE, CACHE_LOCK),
    ]

    for file_path, lock_path in file_lock_pairs:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            try:
                with filelock.FileLock(lock_path, timeout=5):
                    file_path.touch()
                logger.warning(f"File {file_path.name} not found. Created empty file.")
            except Exception as exc:
                logger.error(f"Failed to create file {file_path.name}: {exc}")
                return False

    logger.info("--- BOOTSTRAP CHECK COMPLETED ---")
    return True


def _print_help():
    print("Usage:")
    print("  python main.py")
    print("  python main.py interactive")
    print("  python main.py healthcheck")
    print("  python main.py <card_code>")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("--help", "-h"):
        _print_help()
        return 0

    if args and args[0].lower() == "healthcheck":
        from scripts.healthcheck import main as healthcheck_main

        return healthcheck_main(args[1:])

    first_arg_lower = args[0].lower() if args else None
    is_interactive = first_arg_lower == "interactive"

    if not bootstrap_check(require_telegram=not is_interactive):
        return 1

    if is_interactive:
        try:
            with filelock.FileLock(MAIN_PROCESS_LOCK, timeout=1):
                logger.info("Process lock acquired. STARTING INTERACTIVE MODE (LONG POLLING).")
                run_interactive_bot()
            return 0
        except filelock.Timeout:
            logger.warning("ALERT: Another interactive bot instance is already running. Lock respected. Exiting.")
            return 0
        except Exception as exc:
            logger.critical(f"Error in interactive mode: {exc}", exc_info=True)
            return 1

    card_code_arg = None
    if first_arg_lower and first_arg_lower.isdigit() and 5 <= len(first_arg_lower) <= 6:
        card_code_arg = args[0]

    try:
        from arkham_bot.services.daily_card import post_daily_card

        with filelock.FileLock(MAIN_PROCESS_LOCK, timeout=1):
            mode = "specific_card" if card_code_arg else "cron"
            logger.info(f"Process lock acquired. Starting main execution in mode: {mode}")
            result = asyncio.run(post_daily_card(specific_card_code=card_code_arg))
        if result.success:
            logger.info("Execution finished successfully. Lock released automatically.")
            return 0
        logger.error(f"Execution finished with failure: {result.error}")
        return 1
    except filelock.Timeout:
        logger.warning("ALERT: Another instance is already running. Lock respected. Exiting.")
        return 0
    except Exception as exc:
        logger.critical(f"Uncaught main execution error: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
