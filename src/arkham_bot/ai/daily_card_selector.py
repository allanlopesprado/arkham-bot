import json
import logging
from dataclasses import dataclass

import httpx

from ..config import AI_DAILY_CARD_ENABLED, AI_MODEL, OPENAI_API_KEY, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AIDailyCardChoice:
    selected_card_code: str
    pre_message: str = ""
    post_question: str = ""
    reason: str = ""


def validate_ai_choice(payload: dict, candidate_codes: set[str]) -> AIDailyCardChoice:
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")
    code = str(payload.get("selected_card_code") or "").strip()
    if code not in candidate_codes:
        raise ValueError("AI selected a card outside candidate list")
    pre = str(payload.get("pre_message") or "").strip()
    post = str(payload.get("post_question") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    if len(pre) > 280:
        raise ValueError("AI pre_message too long")
    if len(post) > 220:
        raise ValueError("AI post_question too long")
    if len(reason) > 500:
        reason = reason[:500]
    return AIDailyCardChoice(code, pre, post, reason)


async def choose_daily_card_with_ai(candidates: list[dict], language: str = "pt-BR", tone: str = "misterioso") -> AIDailyCardChoice | None:
    if not AI_DAILY_CARD_ENABLED or not OPENAI_API_KEY or not candidates:
        return None
    candidate_codes = {str(card.get("code")) for card in candidates if card.get("code")}
    compact_cards = [
        {
            "code": card.get("code"),
            "name": card.get("name") or card.get("real_name"),
            "type_code": card.get("type_code"),
            "faction_code": card.get("faction_code"),
            "pack_code": card.get("pack_code"),
            "xp": card.get("xp"),
        }
        for card in candidates[:50]
    ]
    prompt = {
        "task": "Choose one Arkham Horror LCG daily card from candidates only.",
        "language": language,
        "tone": tone,
        "rules": [
            "Return strict JSON only.",
            "Do not invent rules, lore, FAQ, taboo, popularity, or combos.",
            "selected_card_code must be one of the candidates.",
            "pre_message max 280 chars; post_question max 220 chars.",
        ],
        "candidates": compact_cards,
        "schema": {"selected_card_code": "string", "pre_message": "string", "post_question": "string", "reason": "string"},
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": AI_MODEL,
                    "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                },
            )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return validate_ai_choice(json.loads(content), candidate_codes)
    except Exception as exc:
        logger.warning("ai_daily_card_choice_failed: %s", exc)
        return None
