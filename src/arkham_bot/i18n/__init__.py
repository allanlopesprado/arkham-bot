from .strings import EN, PT

_SUPPORTED = {"en-US": EN, "pt-BR": PT}


def get_strings(lang: str | None = None) -> dict[str, str]:
    """
    Returns the string dictionary for the given language code.
    Falls back to English if the language is not supported or not provided.
    If lang is None, reads ai_language from settings automatically.
    """
    if lang is None:
        try:
            from ..repositories.settings_repo import get_setting
            lang = str(get_setting("ai_language", "en-US") or "en-US")
        except Exception:
            lang = "en-US"
    return _SUPPORTED.get(lang, EN)
