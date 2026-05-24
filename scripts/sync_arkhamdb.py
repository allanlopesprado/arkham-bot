import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from arkham_bot.arkhamdb_client import (
    fetch_all_cards_sync,
    fetch_factions_sync,
    fetch_faq_by_card_code_sync,
    fetch_packs_sync,
    fetch_taboos_sync,
)
from arkham_bot.logging_config import setup_logging
from arkham_bot.repositories.audit_repo import create_audit_log
from arkham_bot.repositories.cards_repo import upsert_card
from arkham_bot.repositories.factions_repo import upsert_faction
from arkham_bot.repositories.faq_repo import upsert_faq
from arkham_bot.repositories.packs_repo import upsert_pack
from arkham_bot.repositories.taboos_repo import upsert_taboo
from arkham_bot.supabase_client import get_supabase_client

logger = setup_logging()


def map_card_to_row(card: dict) -> dict:
    return {
        "code": card.get("code"),
        "name": card.get("name") or card.get("real_name"),
        "real_name": card.get("real_name"),
        "type_code": card.get("type_code"),
        "subtype_code": card.get("subtype_code"),
        "faction_code": card.get("faction_code"),
        "faction_name": card.get("faction_name"),
        "pack_code": card.get("pack_code"),
        "pack_name": card.get("pack_name"),
        "position": card.get("position"),
        "xp": card.get("xp"),
        "cost": card.get("cost"),
        "quantity": card.get("quantity"),
        "is_unique": card.get("is_unique"),
        "is_exceptional": card.get("is_exceptional") or card.get("exceptional"),
        "deck_limit": card.get("deck_limit"),
        "text": card.get("text"),
        "real_text": card.get("real_text"),
        "flavor": card.get("flavor"),
        "traits": card.get("traits"),
        "skill_willpower": card.get("skill_willpower"),
        "skill_intellect": card.get("skill_intellect"),
        "skill_combat": card.get("skill_combat"),
        "skill_agility": card.get("skill_agility"),
        "health": card.get("health"),
        "sanity": card.get("sanity"),
        "imagesrc": card.get("imagesrc"),
        "backimagesrc": card.get("backimagesrc"),
        "raw": card,
    }


def _taboo_items(payload) -> list[tuple[str, dict]]:
    if isinstance(payload, dict):
        items = payload.get("taboos") or payload.get("data")
        if isinstance(items, list):
            return [(str(item.get("id") or item.get("code") or idx), item) for idx, item in enumerate(items) if isinstance(item, dict)]
        return [(str(payload.get("id") or payload.get("code") or "current"), payload)]
    if isinstance(payload, list):
        return [(str(item.get("id") or item.get("code") or idx), item) for idx, item in enumerate(payload) if isinstance(item, dict)]
    return []


def sync_arkhamdb(*, dry_run: bool = False, sync_faq: bool = False, faq_limit: int = 0) -> dict:
    create_audit_log("sync_started", "manual_script", {"dry_run": dry_run, "sync_faq": sync_faq})

    cards = fetch_all_cards_sync()
    encounter_cards = fetch_all_cards_sync(include_encounter=True)
    packs = fetch_packs_sync()
    factions = fetch_factions_sync()
    taboos = fetch_taboos_sync()
    taboo_items = _taboo_items(taboos)

    result = {
        "cards_player": len(cards),
        "cards_total_with_encounter": len(encounter_cards),
        "packs": len(packs),
        "factions": len(factions),
        "taboos": len(taboo_items),
        "faq": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info("sync dry-run: %s", result)
        return result

    if not get_supabase_client():
        raise RuntimeError("Supabase not configured")

    for pack in packs:
        upsert_pack(pack)
    for faction in factions:
        upsert_faction(faction)
    for taboo_id, taboo in taboo_items:
        upsert_taboo(taboo_id, taboo)
    for card in encounter_cards:
        upsert_card(map_card_to_row(card))

    if sync_faq:
        faq_cards = encounter_cards[:faq_limit] if faq_limit else encounter_cards
        for card in faq_cards:
            code = card.get("code")
            if not code:
                continue
            try:
                faq = fetch_faq_by_card_code_sync(code)
                upsert_faq(code, faq)
                result["faq"] += 1
            except Exception as exc:
                logger.warning("faq_sync_failed card=%s error=%s", code, exc)

    create_audit_log("sync_arkhamdb_success", "manual_script", result=result)
    logger.info("sync_arkhamdb_success: %s", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sync-faq", action="store_true", help="Also fetch FAQ per card. This can be slower.")
    parser.add_argument("--faq-limit", type=int, default=0, help="Limit FAQ sync count. 0 means no limit.")
    args = parser.parse_args()
    try:
        sync_arkhamdb(dry_run=args.dry_run, sync_faq=args.sync_faq, faq_limit=args.faq_limit)
        return 0
    except Exception as exc:
        logger.error("sync_arkhamdb_failed: %s", exc, exc_info=True)
        create_audit_log("sync_arkhamdb_failed", "manual_script", result={"error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
