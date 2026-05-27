import logging

from . import en, pt_br
from ..repositories.settings_repo import get_setting

logger = logging.getLogger(__name__)

_SUPPORTED = {
    "en-US": en.strings,
    "pt-BR": pt_br.strings,
}


def get_strings(lang: str | None = None) -> dict:
    if lang is None:
        try:
            lang = str(get_setting("ai_language", "pt-BR") or "pt-BR")
        except Exception:
            logger.warning("get_strings: failed to read ai_language from settings, falling back to pt-BR")
            lang = "pt-BR"
    return _SUPPORTED.get(lang, pt_br.strings)
