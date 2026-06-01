import json
import logging
import random
import re
from dataclasses import dataclass

import httpx

from ..core.config import AI_DAILY_CARD_ENABLED, AI_MODEL, GEMINI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, OPENAI_API_KEY, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

TONES = [
    "misterioso",
    "tenso",
    "epico",
    "sombrio",
    "reflexivo",
    "esperancoso",
    "perturbador",
    "melancolico",
]

_TAG_RE = re.compile(r'<[^>]+>|\[[^\]]+\]')

GEMINI_MODELS = {"gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro"}
OPENAI_MODELS = {"gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "gpt-4-turbo"}
GROQ_MODELS = {"llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"}
MISTRAL_MODELS = {"mistral-small-latest", "mistral-medium-latest", "open-mistral-7b"}
VALID_MODELS = GEMINI_MODELS | OPENAI_MODELS | GROQ_MODELS | MISTRAL_MODELS
TEMPERATURE_MAP = {"conservative": 0.5, "default": 0.9, "creative": 1.4}

_OPENAI_COMPAT = {
    "openai":  ("https://api.openai.com/v1/chat/completions",         lambda: OPENAI_API_KEY),
    "groq":    ("https://api.groq.com/openai/v1/chat/completions",    lambda: GROQ_API_KEY),
    "mistral": ("https://api.mistral.ai/v1/chat/completions",         lambda: MISTRAL_API_KEY),
}
_ASYNC_CLIENT: httpx.AsyncClient | None = None


def _get_async_client() -> httpx.AsyncClient:
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is None or _ASYNC_CLIENT.is_closed:
        _ASYNC_CLIENT = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _ASYNC_CLIENT


def _provider(model: str) -> str:
    if model.startswith("gpt-"):
        return "openai"
    if model in GROQ_MODELS:
        return "groq"
    if model in MISTRAL_MODELS:
        return "mistral"
    return "gemini"


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
        pre = pre[:280]
    if len(post) > 220:
        post = post[:220]
    if len(reason) > 500:
        reason = reason[:500]
    return AIDailyCardChoice(code, pre, post, reason)


async def _call_gemini(prompt: dict, model: str, temperature: float) -> dict:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": json.dumps(prompt, ensure_ascii=False)}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }
    client = _get_async_client()
    response = await client.post(url, json=payload)
    if response.status_code != 200:
        logger.error("gemini_error status=%s body=%s", response.status_code, response.text[:500])
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


async def _call_openai_compat(prompt: dict, model: str, temperature: float, provider: str) -> dict:
    url, get_key = _OPENAI_COMPAT[provider]
    headers = {"Authorization": f"Bearer {get_key()}"}
    payload = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
    }
    client = _get_async_client()
    response = await client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    return json.loads(data["choices"][0]["message"]["content"])


async def _call_ai(prompt: dict, model: str, temperature: float) -> dict:
    provider = _provider(model)
    if provider in _OPENAI_COMPAT:
        return await _call_openai_compat(prompt, model, temperature, provider)
    return await _call_gemini(prompt, model, temperature)


def _key_available(model: str) -> bool:
    provider = _provider(model)
    keys = {"openai": OPENAI_API_KEY, "groq": GROQ_API_KEY, "mistral": MISTRAL_API_KEY}
    return bool(keys.get(provider, GEMINI_API_KEY))


async def choose_daily_card_with_ai(
    candidates: list[dict],
    language: str = "pt-BR",
    tone: str | None = None,
    pre_message_enabled: bool = True,
    post_question_enabled: bool = True,
    model: str | None = None,
    creativity: str = "default",
) -> AIDailyCardChoice | None:
    """Selects a card from candidates AND generates commentary for it."""
    if not AI_DAILY_CARD_ENABLED:
        logger.debug("choose_daily_card_with_ai: skipped — AI_DAILY_CARD_ENABLED=false")
        return None
    effective_model = model if model and model in VALID_MODELS else AI_MODEL
    if not _key_available(effective_model):
        provider = _provider(effective_model)
        logger.warning("choose_daily_card_with_ai: skipped — %s API key not configured", provider)
        return None
    if not candidates:
        return None

    effective_tone = tone if tone and tone in TONES else random.choice(TONES)
    temperature = TEMPERATURE_MAP.get(creativity, 0.9)

    visible_candidates = random.sample(candidates, min(50, len(candidates)))
    candidate_codes = {str(card.get("code")) for card in visible_candidates if card.get("code")}
    compact_cards = [_compact(card) for card in visible_candidates]

    rules = [
        "Return strict JSON only — no markdown, no extra keys.",
        "selected_card_code must be exactly one of the candidate codes.",
        "Use the card's traits, text, and flavor as creative inspiration — do not copy them verbatim.",
        f"Both pre_message and post_question must be written in natural {language}.",
        "Do not include Markdown, HTML, links, hashtags, or emojis.",
        f"Tone for this post: {effective_tone}. Let the tone influence word choice and rhythm.",
        "Vary sentence structure — avoid starting both fields with the same word.",
        "Prefer cards with rich text or flavor for a more engaging post.",
    ]
    if pre_message_enabled:
        rules.append("pre_message sets the atmosphere BEFORE the card image is shown — it must stand alone without naming the card. Always end with a short, varied call-to-action inviting the group to see the Card of the Day (e.g. 'Prontos para o card do dia?', 'O card de hoje aguarda...', 'Será que estão preparados?', 'Descubram o card de hoje.' — never repeat the same phrase twice). Max 280 chars total.")
    else:
        rules.append("pre_message must be an empty string.")
    if post_question_enabled:
        rules.append("post_question invites group discussion about the card's mechanics, strategy, or lore. Max 220 chars.")
    else:
        rules.append("post_question must be an empty string.")

    prompt = {
        "task": "Choose one Arkham Horror LCG card as the Card of the Day and write atmospheric commentary for Telegram.",
        "language": language,
        "tone": effective_tone,
        "rules": rules,
        "candidates": compact_cards,
        "schema": {
            "selected_card_code": "string",
            "pre_message": "string — atmospheric intro, no card name, max 280 chars (empty string if disabled)",
            "post_question": "string — discussion prompt about mechanics or lore, max 220 chars (empty string if disabled)",
            "reason": "string — internal reasoning for card selection, not shown to users, max 500 chars",
        },
    }

    try:
        payload = await _call_ai(prompt, model=effective_model, temperature=temperature)
        choice = validate_ai_choice(payload, candidate_codes)
        logger.info("ai_select tone=%s model=%s card=%s", effective_tone, effective_model, choice.selected_card_code)
        return choice
    except Exception as exc:
        logger.warning("ai_daily_card_choice_failed: %s", exc)
        return None


async def generate_card_commentary(
    card: dict,
    language: str = "pt-BR",
    tone: str | None = None,
    pre_message_enabled: bool = True,
    post_question_enabled: bool = True,
    model: str | None = None,
    creativity: str = "default",
) -> AIDailyCardChoice | None:
    """Generates pre_message and post_question for a specific card (used for manual posts)."""
    if not AI_DAILY_CARD_ENABLED:
        logger.debug("generate_card_commentary: skipped — AI_DAILY_CARD_ENABLED=false")
        return None
    effective_model = model if model and model in VALID_MODELS else AI_MODEL
    if not _key_available(effective_model):
        provider = _provider(effective_model)
        logger.warning("generate_card_commentary: skipped — %s API key not configured", provider)
        return None
    if not card:
        return None

    effective_tone = tone if tone and tone in TONES else random.choice(TONES)
    temperature = TEMPERATURE_MAP.get(creativity, 0.9)
    code = str(card.get("code") or "")

    rules = [
        "Return strict JSON only — no markdown, no extra keys.",
        f"selected_card_code must be exactly: {code}",
        "Use the card's traits, text, and flavor as creative inspiration — do not copy them verbatim.",
        f"Both fields must be written in natural {language}.",
        "Do not include Markdown, HTML, links, hashtags, or emojis.",
        f"Tone for this post: {effective_tone}. Let the tone influence word choice and rhythm.",
        "Vary sentence structure — avoid starting both fields with the same word.",
    ]
    if pre_message_enabled:
        rules.append("pre_message sets the atmosphere BEFORE the card image is shown — do not name the card. Max 280 chars.")
    else:
        rules.append("pre_message must be an empty string.")
    if post_question_enabled:
        rules.append("post_question invites group discussion about the card's mechanics, strategy, or lore. Max 220 chars.")
    else:
        rules.append("post_question must be an empty string.")

    prompt = {
        "task": "Write atmospheric Telegram commentary for this Arkham Horror LCG Card of the Day.",
        "language": language,
        "tone": effective_tone,
        "card": _compact(card),
        "rules": rules,
        "schema": {
            "selected_card_code": f"must be exactly: {code}",
            "pre_message": "string — atmospheric intro, no card name, max 280 chars",
            "post_question": "string — discussion prompt about mechanics or lore, max 220 chars",
            "reason": "string — internal note, max 500 chars",
        },
    }

    try:
        payload = await _call_ai(prompt, model=effective_model, temperature=temperature)
        candidate_codes = {code}
        choice = validate_ai_choice(payload, candidate_codes)
        logger.info("ai_comment tone=%s model=%s card=%s", effective_tone, effective_model, code)
        return choice
    except Exception as exc:
        logger.warning("ai_generate_commentary_failed card=%s: %s", code, exc)
        return None
