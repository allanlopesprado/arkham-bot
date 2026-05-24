import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _install_telegram_test_stubs() -> None:
    if importlib.util.find_spec("telegram") is not None:
        return

    telegram = types.ModuleType("telegram")
    constants = types.ModuleType("telegram.constants")
    error = types.ModuleType("telegram.error")
    ext = types.ModuleType("telegram.ext")

    class _Bot:
        def __init__(self, *args, **kwargs):
            pass

    class _InlineKeyboardButton:
        def __init__(self, *args, **kwargs):
            pass

    class _InlineKeyboardMarkup:
        def __init__(self, *args, **kwargs):
            pass

    class _Update:
        pass

    class _ParseMode:
        HTML = "HTML"
        MARKDOWN = "Markdown"

    class _TelegramError(Exception):
        pass

    class _RetryAfter(_TelegramError):
        def __init__(self, retry_after=1):
            super().__init__("RetryAfter")
            self.retry_after = retry_after

    class _Handler:
        def __init__(self, *args, **kwargs):
            pass

    class _ConversationHandler(_Handler):
        END = -1
        def __init__(self, *args, **kwargs):
            pass

    class _ContextTypes:
        DEFAULT_TYPE = object

    class _Filters:
        TEXT = object()
        COMMAND = object()
        @staticmethod
        def Regex(*args, **kwargs):
            return object()

    telegram.Bot = _Bot
    telegram.InlineKeyboardButton = _InlineKeyboardButton
    telegram.InlineKeyboardMarkup = _InlineKeyboardMarkup
    telegram.Update = _Update
    constants.ParseMode = _ParseMode
    error.TelegramError = _TelegramError
    error.RetryAfter = _RetryAfter
    ext.CallbackQueryHandler = _Handler
    ext.CommandHandler = _Handler
    ext.MessageHandler = _Handler
    ext.ConversationHandler = _ConversationHandler
    ext.ContextTypes = _ContextTypes
    ext.filters = _Filters

    sys.modules["telegram"] = telegram
    sys.modules["telegram.constants"] = constants
    sys.modules["telegram.error"] = error
    sys.modules["telegram.ext"] = ext


def _install_tenacity_test_stubs() -> None:
    if importlib.util.find_spec("tenacity") is not None:
        return
    tenacity = types.ModuleType("tenacity")

    class _RetryCondition:
        def __or__(self, other):
            return self

    def retry(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def _condition(*args, **kwargs):
        return _RetryCondition()

    def _noop(*args, **kwargs):
        return None

    tenacity.retry = retry
    tenacity.retry_if_exception = _condition
    tenacity.retry_if_exception_type = _condition
    tenacity.stop_after_attempt = _noop
    tenacity.wait_exponential = _noop
    sys.modules["tenacity"] = tenacity


_install_tenacity_test_stubs()
_install_telegram_test_stubs()
