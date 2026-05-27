import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from .config import (
    DEBUG_DIR,
    ENVIRONMENT,
    ERROR_LOG_FILE,
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_MAX_BYTES,
    OPENAI_API_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    TELEGRAM_BOT_TOKEN,
    ensure_runtime_dirs,
)


SENSITIVE_LOGGER_NAMES = ("httpx", "httpcore", "telegram", "telegram.ext")
TELEGRAM_BOT_TOKEN_RE = re.compile(r"bot[0-9]+:[A-Za-z0-9_-]+")
SECRET_NAME_RE = re.compile(r"\b(TELEGRAM_BOT_TOKEN|SUPABASE_SERVICE_ROLE_KEY|OPENAI_API_KEY)\b")
REDACTED_SECRET = "[REDACTED]"


def _mask_secrets(message: str) -> str:
    masked = TELEGRAM_BOT_TOKEN_RE.sub(f"bot{REDACTED_SECRET}", message)
    masked = SECRET_NAME_RE.sub(REDACTED_SECRET, masked)

    for secret in (TELEGRAM_BOT_TOKEN, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY):
        if secret:
            masked = masked.replace(secret, REDACTED_SECRET)

    return masked


class SecretMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _mask_secrets(record.getMessage())
        record.args = ()
        return True


class SecretMaskingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _mask_secrets(super().format(record))


def _configure_library_loggers() -> None:
    # Always silence noisy HTTP-level loggers — individual requests are never useful in app logs
    for logger_name in ("httpx", "httpcore", "hpack"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # In non-prod, keep telegram at INFO so polling/dispatch events are visible
    if ENVIRONMENT.lower() in {"prod", "production"}:
        for logger_name in ("telegram", "telegram.ext", "apscheduler"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)


def _add_secret_filter(target: logging.Filterer) -> None:
    if not any(isinstance(log_filter, SecretMaskingFilter) for log_filter in target.filters):
        target.addFilter(SecretMaskingFilter())


def setup_logging():
    """Configures console and rotating file logging."""
    ensure_runtime_dirs()
    _configure_library_loggers()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    _add_secret_filter(logger)
    for logger_name in SENSITIVE_LOGGER_NAMES:
        _add_secret_filter(logging.getLogger(logger_name))

    if logger.handlers:
        for handler in logger.handlers:
            _add_secret_filter(handler)
        return logger

    formatter = SecretMaskingFormatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(SecretMaskingFormatter('%(levelname)s: %(message)s'))
    _add_secret_filter(console_handler)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    _add_secret_filter(file_handler)
    logger.addHandler(file_handler)

    error_handler = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    _add_secret_filter(error_handler)
    logger.addHandler(error_handler)

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    return logger
