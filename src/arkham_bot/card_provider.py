import logging

from .arkhamdb_client import fetch_card_by_code_async, fetch_card_by_code_sync
from .repositories.cards_repo import get_card_by_code


logger = logging.getLogger(__name__)


def get_card(card_code: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    # DB first
    if allow_cache:
        try:
            cached = get_card_by_code(card_code)
            if cached:
                raw = cached.get("raw") or cached
                raw["spoiler"] = cached.get("spoiler") or raw.get("spoiler") or False
                if raw.get("double_sided") and not raw.get("back_text") and not raw.get("back_flavor"):
                    logger.debug(f"DB card {card_code} is double_sided but missing back data, fetching from API")
                else:
                    return raw, "db"
        except Exception as exc:
            logger.warning(f"DB card fetch failed for {card_code}: {exc}")
    # API fallback
    try:
        return fetch_card_by_code_sync(card_code), "arkhamdb"
    except Exception as exc:
        logger.warning(f"ArkhamDB card fetch failed for {card_code}: {exc}")
    return None, "not_found"


async def get_card_async(card_code: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    # DB first
    if allow_cache:
        try:
            cached = get_card_by_code(card_code)
            if cached:
                raw = cached.get("raw") or cached
                raw["spoiler"] = cached.get("spoiler") or raw.get("spoiler") or False
                # Double-sided cards synced from list endpoint may lack back_text — fall through to API
                if raw.get("double_sided") and not raw.get("back_text") and not raw.get("back_flavor"):
                    logger.debug(f"DB card {card_code} is double_sided but missing back data, fetching from API")
                else:
                    return raw, "db"
        except Exception as exc:
            logger.warning(f"DB card fetch failed for {card_code}: {exc}")
    # API fallback
    try:
        return await fetch_card_by_code_async(card_code), "arkhamdb"
    except Exception as exc:
        logger.warning(f"ArkhamDB card fetch failed for {card_code}: {exc}")
    return None, "not_found"
