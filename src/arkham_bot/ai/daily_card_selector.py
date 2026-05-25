import json
import logging
import random
import re
from dataclasses import dataclass

import httpx

from ..config import AI_DAILY_CARD_ENABLED, AI_MODEL, OPENAI_API_KEY, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

TONES = [
    "misterioso",
    "tenso",
    "épico",
    "sombrio",
    "reflexivo",
    "esperançoso",
    "perturbador",
    "melancólico",
]

_TAG_RE = re.compile(r'<[^>]+>|\[[^\]]+\]')


def _strip(text: str | None, limit: int) -> str:
    if not text:
        return ""
    clean = _TAG_RE.sub('', text).strip()
    return clean[:limit] if len(clean) > limit else clean


def _compact(card: dict) -> dict:
    return {
        "code": card.get("code"),
        "name": card.get("name") or card.get("real_name"),
        "type_code": card.get("type_code"),
        "faction_code": card.get("faction_code"),
        "pack_code": card.get("pack_code"),
        "xp": card.get("xp"),
        "traits": _strip(card.get("traits") or card.get("real_traits") or "", 120),
        "text": _strip(card.get("text") or card.get("real_text") or "", 400),
        "flavor": _strip(card.get("flavor") or "", 200),
    }


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


async def choose_daily_card_with_ai(candidates: list[dict], language: str = "pt-BR") -> AIDailyCardChoice | None:
    if not AI_DAILY_CARD_ENABLED or not OPENAI_API_KEY or not candidates:
        return None

    tone = random.choice(TONES)
    candidate_codes = {str(card.get("code")) for card in candidates if card.get("code")}
    compact_cards = [_compact(card) for card in candidates[:50]]

    prompt = {
        "task": "Choose one Arkham Horror LCG card as the Card of the Day and write atmospheric commentary for Telegram.",
        "language": language,
        "tone": tone,
        "rules": [
            "Return strict JSON only — no markdown, no extra keys.",
            "selected_card_code must be exactly one of the candidate codes.",
            "Use the card's traits, text, and flavor as creative inspiration — do not copy them verbatim.",
            "pre_message sets the atmosphere BEFORE the card image is shown — it must stand alone without naming the card.",
            "post_question invites group discussion about the card's mechanics, strategy, or lore.",
            f"Both pre_message and post_question must be written in natural {language}.",
            "Do not include Markdown, HTML, links, hashtags, or emojis.",
            "pre_message max 280 chars. post_question max 220 chars.",
            f"Tone for this post: {tone}. Let the tone influence word choice and rhythm.",
            "Vary sentence structure — avoid starting both fields with the same word.",
            "Prefer cards with rich text or flavor for a more engaging post.",
        ],
        "candidates": compact_cards,
        "schema": {
            "selected_card_code": "string",
            "pre_message": "string — atmospheric intro, no card name, max 280 chars",
            "post_question": "string — discussion prompt about mechanics or lore, max 220 chars",
            "reason": "string — internal reasoning for card selection, not shown to users, max 500 chars",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": AI_MODEL,
                    "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                    "temperature": 0.9,
                    "response_format": {"type": "json_object"},
                },
            )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        choice = validate_ai_choice(json.loads(content), candidate_codes)
        logger.info("ai_tone=%s card=%s", tone, choice.selected_card_code)
        return choice
    except Exception as exc:
        logger.warning("ai_daily_card_choice_failed: %s", exc)
        return None
