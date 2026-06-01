import asyncio
import logging

from ..clients.arkhamdb_client import fetch_card_by_code_async, fetch_card_by_code_sync
from ..repositories.cards_repo import get_card_by_code


logger = logging.getLogger(__name__)


def _card_from_db_row(cached: dict) -> dict | None:
    """Extract and prepare card dict from a DB row. Returns None if back data missing for double_sided."""
    raw = cached.get("raw")
    if not raw:
        return None
    # DB spoiler column takes precedence (admin-controlled) over ArkhamDB value
    raw["spoiler"] = bool(cached.get("spoiler")) or bool(raw.get("spoiler"))
    # If double_sided but no back data in raw, need API for complete card
    if cached.get("double_sided") and not raw.get("back_text") and not raw.get("back_flavor"):
        return None
    return raw


def get_card(card_code: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    if allow_cache:
        try:
            cached = get_card_by_code(card_code)
            if cached:
                raw = _card_from_db_row(cached)
                if raw is not None:
                    return raw, "db"
                logger.debug(f"DB card {card_code} double_sided missing back data, fetching from API")
        except Exception as exc:
            logger.warning(f"DB card fetch failed for {card_code}: {exc}")
    try:
        return fetch_card_by_code_sync(card_code), "arkhamdb"
    except Exception as exc:
        logger.warning(f"ArkhamDB card fetch failed for {card_code}: {exc}")
    return None, "not_found"


async def get_card_async(card_code: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    if allow_cache:
        try:
            cached = await asyncio.to_thread(get_card_by_code, card_code)
            if cached:
                raw = _card_from_db_row(cached)
                if raw is not None:
                    return raw, "db"
                logger.debug(f"DB card {card_code} double_sided missing back data, fetching from API")
        except Exception as exc:
            logger.warning(f"DB card fetch failed for {card_code}: {exc}")
    try:
        return await fetch_card_by_code_async(card_code), "arkhamdb"
    except Exception as exc:
        logger.warning(f"ArkhamDB card fetch failed for {card_code}: {exc}")
    return None, "not_found"
