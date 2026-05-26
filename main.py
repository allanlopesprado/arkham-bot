import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import filelock

from arkham_bot.config import (
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
from arkham_bot.logging_config import setup_logging


logger = setup_logging()


async def interactive_post_init(application):
    from telegram import BotCommand
    from arkham_bot.scheduler import start_daily_scheduler
    from arkham_bot.telegram_handlers import bot_started_message

    await application.bot.set_my_commands([
        BotCommand("start",      "Inicia o bot"),
        BotCommand("help",       "Ajuda e comandos disponíveis"),
        BotCommand("menu",       "Abre o menu principal"),
        BotCommand("today",      "Card do dia atual"),
        BotCommand("random",     "Card aleatório"),
        BotCommand("search",     "Busca cartas por nome"),
        BotCommand("sets",       "Navega cartas por set/expansão"),
        BotCommand("card",       "Busca carta por código"),
        BotCommand("status",     "Status do bot"),
        BotCommand("chatid",     "Mostra o ID deste chat"),
        BotCommand("ai_test",    "Testa a configuração da IA"),
    ])
    await bot_started_message(application)
    start_daily_scheduler(application)


def run_interactive_bot():
    """Runs the bot in Long Polling mode using ApplicationBuilder."""
    from telegram.ext import ApplicationBuilder
    from arkham_bot.telegram_handlers import register_handlers

    logger.info("--- STARTING INTERACTIVE MODE (LONG POLLING) ---")

    if not TELEGRAM_BOT_TOKEN:
        logger.critical("Telegram token not configured for interactive mode.")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(interactive_post_init).build()
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
        from arkham_bot.daily_card import post_daily_card

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
