import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DEBUG_DIR = LOG_DIR / "debug_logs"

DEFAULT_TIMEZONE = "America/Sao_Paulo"
TIMEZONE = os.getenv("TIMEZONE", DEFAULT_TIMEZONE)
DAILY_POST_ENABLED = os.getenv("DAILY_POST_ENABLED", "true").lower() == "true"
DAILY_POST_TIMES = [item.strip() for item in os.getenv("DAILY_POST_TIMES", "08:00").split(",") if item.strip()]
DAILY_POST_DAYS = [item.strip() for item in os.getenv("DAILY_POST_DAYS", "mon,tue,wed,thu,fri,sat,sun").split(",") if item.strip()]
DAILY_SCHEDULER_MODE = "internal_bot_loop"

# File and Lock Configurations
POSTED_CARDS_FILE = DATA_DIR / "posted_cards.txt"
POSTED_CARDS_LOCK = DATA_DIR / "posted_cards.txt.lock"
HISTORY_FILE = LOG_DIR / "posting_history.log"
CACHE_FILE = DATA_DIR / "card_cache.json"
CACHE_LOCK = DATA_DIR / "card_cache.json.lock"
MAIN_PROCESS_LOCK = DATA_DIR / "main_process.lock"
DAILY_SCHEDULER_STATE_FILE = DATA_DIR / "daily_scheduler_state.json"
LAST_PINNED_DAILY_CARD_FILE = DATA_DIR / "last_pinned_daily_card.json"

# Operation and Security Configurations
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

BASE_URL = "https://arkhamdb.com/"
ARKHAMDB_API_URL = "https://arkhamdb.com/api/public/cards/"
ARKHAM_CARD_API_URL = "https://arkhamdb.com/api/public/card/"

CACHE_EXPIRATION_SECONDS = 24 * 60 * 60
EXTENSIONS_TO_TRY = ['.png', '.jpg', '.jpeg']

# Logging Configurations
LOG_FILE = LOG_DIR / "bot_execution.log"
ERROR_LOG_FILE = LOG_DIR / "bot_errors.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# Retry Constants
MAX_RETRIES = 5
INITIAL_BACKOFF = 2
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

# State Constants
CHOOSING_CARD_NUMBER = 0
CALLBACK_CANCEL = 'CANCEL_CONV'

# Public command rate limiting
PUBLIC_COMMANDS_RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_USER_MAX_REQUESTS = 10
RATE_LIMIT_PER_USER_WINDOW_SECONDS = 60
RATE_LIMIT_PER_CHAT_MAX_REQUESTS = 60
RATE_LIMIT_PER_CHAT_WINDOW_SECONDS = 60
RATE_LIMIT_EXEMPT_ADMINS = True
RATE_LIMIT_EXCEEDED_MESSAGE_PT = "Muitas solicitações em pouco tempo. Aguarde alguns segundos e tente novamente."
RATE_LIMIT_EXCEEDED_MESSAGE_EN = "Too many requests in a short time. Please wait a few seconds and try again."


# Admins and AI
def _parse_int_set(raw: str | None) -> set[int]:
    values: set[int] = set()
    if not raw:
        return values
    for item in raw.split(','):
        item = item.strip()
        if not item:
            continue
        try:
            values.add(int(item))
        except ValueError:
            continue
    return values

ADMIN_TELEGRAM_USER_IDS = _parse_int_set(os.getenv("ADMIN_TELEGRAM_USER_IDS"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
ARKHAMDB_OAUTH_CLIENT_ID = os.getenv("ARKHAMDB_OAUTH_CLIENT_ID")
ARKHAMDB_OAUTH_CLIENT_SECRET = os.getenv("ARKHAMDB_OAUTH_CLIENT_SECRET")
AI_DAILY_CARD_ENABLED = os.getenv("AI_DAILY_CARD_ENABLED", "true").lower() == "true"
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")

# Bot command polling
BOT_COMMANDS_POLLING_ENABLED = os.getenv("BOT_COMMANDS_POLLING_ENABLED", "true").lower() == "true"
BOT_COMMANDS_POLLING_INTERVAL_SECONDS = int(os.getenv("BOT_COMMANDS_POLLING_INTERVAL_SECONDS", "30"))
BOT_COMMANDS_BATCH_SIZE = int(os.getenv("BOT_COMMANDS_BATCH_SIZE", "10"))
BOT_COMMANDS_MAX_RETRIES = int(os.getenv("BOT_COMMANDS_MAX_RETRIES", "3"))
BOT_COMMANDS_RETRY_DELAY_SECONDS = int(os.getenv("BOT_COMMANDS_RETRY_DELAY_SECONDS", "60"))
BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS = int(os.getenv("BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS", "900"))

# Mapping for the /card command
PACK_CODES = {
    'Core': '01',
    'The Dunwich Legacy': '02',
    'The Path to Carcosa': '03',
    'The Forgotten Age': '04',
    'The Circle Undone': '05',
    'The Dream-Eaters': '06',
    'The Innsmouth Conspiracy': '07',
    'Edge of the Earth': '08',
    'The Scarlet Keys': '09',
    'The Feast of Hemlock Vale': '10',
    'The Drowned City': '11',
    'Return to the Path to Carcosa': '12',
    'Investigator Starter Decks': '13',
    'Side Stories': '14',
    'Promotional': '15',
    'Parallel': '16',
}


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, LOG_DIR, DEBUG_DIR):
        path.mkdir(parents=True, exist_ok=True)
