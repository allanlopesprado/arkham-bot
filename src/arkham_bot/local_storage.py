import json
import logging
import os
import shutil
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import filelock

from .config import (
    CACHE_EXPIRATION_SECONDS,
    CACHE_FILE,
    CACHE_LOCK,
    DEBUG_DIR,
    HISTORY_FILE,
    LAST_PINNED_DAILY_CARD_FILE,
    POSTED_CARDS_FILE,
    POSTED_CARDS_LOCK,
    ensure_runtime_dirs,
)


logger = logging.getLogger(__name__)


def safe_atomic_write(data, target_path: Path, lock_path: Path, data_type='text'):
    """Writes data to a file atomically and with file locking."""
    ensure_runtime_dirs()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = Path(tempfile.mktemp(dir=target_path.parent))

    try:
        with filelock.FileLock(lock_path, timeout=10):
            with open(temp_file, 'w', encoding='utf-8') as f:
                if data_type == 'json':
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    f.write(data)
            shutil.move(temp_file, target_path)
    except Exception as e:
        logger.error(f"Failed atomic write for {target_path.name}: {e}")
        raise
    finally:
        if temp_file.exists():
            os.remove(temp_file)


def load_json_file(path: Path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        logger.warning(f"Failed to load JSON file {path}: {exc}")
        return default


def save_json_file(path: Path, payload: dict, lock_path: Path | None = None) -> None:
    lock = lock_path or path.with_suffix(path.suffix + '.lock')
    safe_atomic_write(payload, path, lock, data_type='json')


def load_posted_cards():
    """Loads posted cards with locking and error handling."""
    try:
        ensure_runtime_dirs()
        with filelock.FileLock(POSTED_CARDS_LOCK, timeout=10):
            if not POSTED_CARDS_FILE.exists():
                return set()
            with open(POSTED_CARDS_FILE, 'r', encoding='utf-8') as f:
                return set(f.read().splitlines())
    except (FileNotFoundError, filelock.Timeout):
        return set()
    except Exception as e:
        logger.error(f"Error loading posted cards: {e}")
        return set()


def save_posted_card(card_code):
    """Adds and saves the card code as posted."""
    current_cards = load_posted_cards()
    current_cards.add(card_code)
    data_to_save = '\n'.join(sorted(current_cards)) + '\n'
    try:
        safe_atomic_write(data_to_save, POSTED_CARDS_FILE, POSTED_CARDS_LOCK, data_type='text')
    except Exception:
        logger.critical(f"CRITICAL: Failed to mark card {card_code} as posted after Telegram success. Data inconsistency risk.")
        raise


def load_card_cache():
    """Loads the card cache if not expired."""
    try:
        ensure_runtime_dirs()
        with filelock.FileLock(CACHE_LOCK, timeout=10):
            if not CACHE_FILE.exists():
                return None
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            timestamp_str = data.get('timestamp')
            cached_cards = data.get('cards')

            if not timestamp_str or not cached_cards:
                raise ValueError("Cache file is invalid.")

            last_fetch = datetime.fromisoformat(timestamp_str)
            if last_fetch.tzinfo is not None:
                last_fetch = last_fetch.astimezone(None).replace(tzinfo=None)

            if datetime.now() < last_fetch + timedelta(seconds=CACHE_EXPIRATION_SECONDS):
                return cached_cards

            return None
    except json.JSONDecodeError:
        logger.error("Corrupted cache file (JSONDecodeError). Deleting and forcing reload.")
        if CACHE_FILE.exists():
            os.remove(CACHE_FILE)
        return None
    except (FileNotFoundError, ValueError, filelock.Timeout):
        return None
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}. Reloading via API.")
        return None


def save_card_cache(cards):
    """Saves card data to cache atomically."""
    data = {'timestamp': datetime.now().isoformat(), 'cards': cards}
    try:
        safe_atomic_write(data, CACHE_FILE, CACHE_LOCK, data_type='json')
        logger.info(f"API cache saved with {len(cards)} cards.")
    except Exception:
        logger.critical("CRITICAL: Failed to save card cache.")
        raise


def log_posting_history(card_code, card_name, status):
    """Logs the posting event history."""
    try:
        ensure_runtime_dirs()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {status}: {card_code} - {card_name}\n"
        with filelock.FileLock(HISTORY_FILE.with_suffix(".lock"), timeout=10):
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
    except Exception as e:
        logger.error(f"Error logging history: {e}")


def log_error_to_file(context, error_message, card_code=None):
    """Saves a detailed debug log to a separate file."""
    ensure_runtime_dirs()
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_name = f"{card_code or 'UNKNOWN'}_{now}_debug.txt"
    file_path = DEBUG_DIR / file_name

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("==== DEBUG LOG ====\n")
        f.write(f"Time: {now}\n")
        f.write(f"Context: {context}\n")
        if card_code:
            f.write(f"Card Code: {card_code}\n")
        f.write("\n--- ERROR MESSAGE ---\n")
        f.write(error_message)
        f.write("\n\n--- STACKTRACE ---\n")
        f.write(traceback.format_exc())


def load_last_pinned_daily_card() -> dict | None:
    payload = load_json_file(LAST_PINNED_DAILY_CARD_FILE, default=None)
    return payload if isinstance(payload, dict) else None


def save_last_pinned_daily_card(payload: dict) -> None:
    save_json_file(LAST_PINNED_DAILY_CARD_FILE, payload)
