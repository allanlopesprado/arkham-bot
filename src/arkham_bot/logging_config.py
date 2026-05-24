import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import (
    DEBUG_DIR,
    ERROR_LOG_FILE,
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_MAX_BYTES,
    ensure_runtime_dirs,
)


def setup_logging():
    """Configures console and rotating file logging."""
    ensure_runtime_dirs()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    error_handler = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    return logger
