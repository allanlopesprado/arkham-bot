# telegram_handlers.py — backward-compatibility shim
# Code now lives in separate handler modules. This file re-exports everything.
from .common import *  # noqa: F401, F403
from .status_handler import *  # noqa: F401, F403
from .card_handler import *  # noqa: F401, F403
from .search_handler import *  # noqa: F401, F403
from .sets_handler import *  # noqa: F401, F403
from .taboo_handler import *  # noqa: F401, F403
from .faq_handler import *  # noqa: F401, F403
from .decklist_handler import *  # noqa: F401, F403
from .cotd_handler import *  # noqa: F401, F403
from .registry import register_handlers  # noqa: F401

# Explicit re-exports of private names accessed by tests and external callers
from .common import (  # noqa: F401
    BOT_STARTED_AT,
    _chunks,
    _arkhamdb_html_to_telegram,
    _fetch_all_cards,
    _cards_cache,
    _cards_encounter_cache,
    _as_bool,
    _format_uptime,
)
from .status_handler import (  # noqa: F401
    _format_status,
    _format_help_report,
    _collect_status_payload,
    bot_started_message,
)
