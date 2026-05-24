import logging

from .arkhamdb_client import fetch_card_by_code_async, fetch_card_by_code_sync
from .repositories.cards_repo import get_card_by_code


logger = logging.getLogger(__name__)


def get_card(card_code: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    try:
        return fetch_card_by_code_sync(card_code), "arkhamdb"
    except Exception as exc:
        logger.warning(f"ArkhamDB card fetch failed for {card_code}: {exc}")
        if allow_cache:
            cached = get_card_by_code(card_code)
            if cached:
                return cached.get("raw") or cached, "supabase_cache"
        return None, "not_found"


async def get_card_async(card_code: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    try:
        return await fetch_card_by_code_async(card_code), "arkhamdb"
    except Exception as exc:
        logger.warning(f"ArkhamDB card fetch failed for {card_code}: {exc}")
        if allow_cache:
            cached = get_card_by_code(card_code)
            if cached:
                return cached.get("raw") or cached, "supabase_cache"
        return None, "not_found"
