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
from arkham_bot.repositories.cards_repo import bulk_upsert_cards
from arkham_bot.repositories.factions_repo import upsert_faction
from arkham_bot.repositories.faq_repo import upsert_faq
from arkham_bot.repositories.packs_repo import upsert_pack
from arkham_bot.repositories.taboos_repo import upsert_taboo
from arkham_bot.supabase_client import get_supabase_client

logger = setup_logging()



def _taboo_items(payload) -> list[tuple[str, dict]]:
    if isinstance(payload, dict):
        items = payload.get("taboos") or payload.get("data")
        if isinstance(items, list):
            return [(str(item.get("id") or item.get("code") or idx), item) for idx, item in enumerate(items) if isinstance(item, dict)]
        return [(str(payload.get("id") or payload.get("code") or "current"), payload)]
    if isinstance(payload, list):
        return [(str(item.get("id") or item.get("code") or idx), item) for idx, item in enumerate(payload) if isinstance(item, dict)]
    return []


BATCH_SIZE = 100


def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def sync_arkhamdb(*, dry_run: bool = False, sync_faq: bool = False, faq_limit: int = 0) -> dict:
    create_audit_log("sync_started", "manual_script", {"dry_run": dry_run, "sync_faq": sync_faq})

    logger.info("Buscando dados do ArkhamDB...")
    logger.info("  Cartas de jogador...")
    cards = fetch_all_cards_sync()
    logger.info("  Todas as cartas (incluindo encontro)...")
    encounter_cards = fetch_all_cards_sync(include_encounter=True)
    logger.info("  Packs, facções, taboos...")
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

    logger.info(
        "Dados recebidos: %d cartas (%d jogador), %d packs, %d facções, %d taboos",
        result["cards_total_with_encounter"], result["cards_player"],
        result["packs"], result["factions"], result["taboos"],
    )

    if dry_run:
        logger.info("sync dry-run: %s", result)
        return result

    if not get_supabase_client():
        raise RuntimeError("Supabase not configurado")

    logger.info("Salvando packs e facções...")
    for pack in packs:
        upsert_pack(pack)
    for faction in factions:
        upsert_faction(faction)

    logger.info("Salvando taboos...")
    for taboo_id, taboo in taboo_items:
        upsert_taboo(taboo_id, taboo)

    total = len(encounter_cards)
    logger.info("Salvando %d cartas em batches de %d...", total, BATCH_SIZE)
    saved = 0
    for batch in _batched(encounter_cards, BATCH_SIZE):
        bulk_upsert_cards(batch)
        saved += len(batch)
        logger.info("  %d/%d cartas salvas", saved, total)

    if sync_faq:
        faq_cards = encounter_cards[:faq_limit] if faq_limit else encounter_cards
        logger.info("Sincronizando FAQ para %d cartas...", len(faq_cards))
        for i, card in enumerate(faq_cards, 1):
            code = card.get("code")
            if not code:
                continue
            try:
                faq = fetch_faq_by_card_code_sync(code)
                upsert_faq(code, faq)
                result["faq"] += 1
            except Exception as exc:
                logger.warning("faq_sync_failed card=%s error=%s", code, exc)
            if i % 50 == 0:
                logger.info("  FAQ: %d/%d cartas processadas", i, len(faq_cards))

    # Verify count in DB matches what we received from ArkhamDB
    client = get_supabase_client()
    db_count = client.count("arkham_cards") if client else None
    api_count = len(encounter_cards)
    if db_count is not None and db_count != api_count:
        logger.warning(
            "DIVERGÊNCIA: ArkhamDB retornou %d cartas mas DB tem %d. "
            "Pode haver cartas duplicadas ou falha em algum batch.",
            api_count, db_count,
        )
    else:
        logger.info("Verificação OK: %d cartas no DB == %d cartas da API", db_count, api_count)

    result["db_cards_count"] = db_count
    create_audit_log("sync_arkhamdb_success", "manual_script", result=result)
    logger.info("Sync concluído: %s", result)
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
