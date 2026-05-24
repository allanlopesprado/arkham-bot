from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from arkham_bot.arkhamdb_client import (
    fetch_all_cards_sync,
    fetch_card_by_code_sync,
    fetch_cards_by_pack_sync,
    fetch_decklist_sync,
    fetch_factions_sync,
    fetch_faq_by_card_code_sync,
    fetch_packs_sync,
    fetch_taboos_sync,
)


OUT_DIR = ROOT_DIR / "data" / "arkhamdb_samples"


def write_json(name: str, data) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def observed_keys(data) -> list[str]:
    if isinstance(data, dict):
        return sorted(data.keys())
    if isinstance(data, list):
        keys = set()
        for item in data:
            if isinstance(item, dict):
                keys.update(item.keys())
        return sorted(keys)
    return []


def run_resource(statuses: list[dict], name: str, endpoint: str, filename: str, fetcher):
    try:
        data = fetcher()
    except Exception as exc:
        statuses.append({"name": name, "endpoint": endpoint, "status": f"failed: {exc}"})
        return None
    write_json(filename, data)
    statuses.append({
        "name": name,
        "endpoint": endpoint,
        "status": "success",
        "keys": observed_keys(data),
    })
    return data


def summarize(cards: list[dict], packs: list[dict], factions: list[dict], statuses: list[dict]) -> str:
    type_counts = Counter(card.get("type_code", "unknown") for card in cards)
    all_keys = [set(card.keys()) for card in cards]
    common_fields = sorted(set.intersection(*all_keys)) if all_keys else []
    null_fields = sorted({key for card in cards for key, value in card.items() if value is None})
    fields_by_type: dict[str, set[str]] = defaultdict(set)

    for card in cards:
        fields_by_type[card.get("type_code", "unknown")].update(card.keys())

    lines = [
        "# ArkhamDB Schema Report",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        "- Official resources evaluated: Card, Pack, Faction, Faq, Taboo, Decklist",
        "- OAuth future resources not tested: Collection, Deck",
        f"- Total cards: {len(cards)}",
        f"- Total packs: {len(packs)}",
        f"- Total factions: {len(factions)}",
        f"- Type codes: {dict(sorted(type_counts.items()))}",
        f"- Fields present in all cards: {common_fields}",
        f"- Fields observed as null: {null_fields}",
        "",
        "## Resource Status",
    ]
    for item in statuses:
        lines.append(f"- {item['name']}: {item['status']} ({item['endpoint']})")
        if item.get("keys"):
            lines.append(f"  - Observed keys: {item['keys']}")

    lines.extend(["", "## Fields By Type"])
    for type_code, fields in sorted(fields_by_type.items()):
        lines.append(f"- {type_code}: {sorted(fields)}")

    lines.extend([
        "",
        "## Pending",
        "- Decklist sample requires ARKHAMDB_SAMPLE_DECKLIST_ID.",
        "- Collection, Deck authenticated, and ArkhamDB OAuth are future work.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    statuses: list[dict] = []

    cards = run_resource(statuses, "Card list", "/api/public/cards/", "cards_player.json", fetch_all_cards_sync) or []
    cards_with_encounter = run_resource(
        statuses,
        "Card list with encounter",
        "/api/public/cards/?encounter=1",
        "cards_with_encounter.json",
        lambda: fetch_all_cards_sync(include_encounter=True),
    ) or cards
    run_resource(statuses, "Card individual", "/api/public/card/01001", "card_01001.json", lambda: fetch_card_by_code_sync("01001"))
    run_resource(statuses, "Cards by pack", "/api/public/cards/core", "cards_by_pack_01.json", lambda: fetch_cards_by_pack_sync("core"))
    packs = run_resource(statuses, "Pack", "/api/public/packs/", "packs.json", fetch_packs_sync) or []
    factions = run_resource(statuses, "Faction", "/api/public/factions/", "factions.json", fetch_factions_sync) or []
    run_resource(statuses, "Faq", "/api/public/faq/01001", "faq_01001.json", lambda: fetch_faq_by_card_code_sync("01001"))
    run_resource(statuses, "Taboo", "/api/public/taboos/", "taboos.json", fetch_taboos_sync)

    decklist_id = os.getenv("ARKHAMDB_SAMPLE_DECKLIST_ID")
    if decklist_id:
        run_resource(
            statuses,
            "Decklist",
            f"/api/public/decklist/{decklist_id}",
            "decklist_sample.json",
            lambda: fetch_decklist_sync(decklist_id),
        )
    else:
        statuses.append({
            "name": "Decklist",
            "endpoint": "/api/public/decklist/{decklist_id}",
            "status": "skipped: ARKHAMDB_SAMPLE_DECKLIST_ID not configured",
        })

    (OUT_DIR / "schema_report.md").write_text(
        summarize(cards_with_encounter, packs, factions, statuses),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
