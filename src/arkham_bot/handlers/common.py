import asyncio
import io
import logging
import re
from datetime import UTC, datetime, timedelta
from html import escape
from urllib.parse import urljoin

from PIL import Image
from telegram import Update
from telegram.constants import ParseMode

from ..clients.arkhamdb_client import download_image_async
from ..core.config import BASE_URL, EXTENSIONS_TO_TRY
from ..core.permissions import is_admin_user
from ..core.rate_limiter import rate_limiter
from ..repositories.cards_repo import get_card_packs

logger = logging.getLogger(__name__)

_pack_list_cache: list[dict] = []
_pack_list_cache_ts: float = 0.0
_PACK_LIST_TTL = 3600.0  # 1 hour

_cards_cache: list[dict] = []
_cards_cache_ts: float = 0.0
_cards_encounter_cache: list[dict] = []
_cards_encounter_cache_ts: float = 0.0
_CARDS_CACHE_TTL = 600.0  # 10 minutes

_FAQ_CACHE_TTL_DAYS = 7
_DECKLIST_CACHE_TTL_HOURS = 24

_CARD_PAGE_SIZE = 10
_SETS_PAGE_SIZE = 10
_TABOO_PAGE_SIZE = 5

BOT_STARTED_AT = datetime.now(UTC)

PACK_ABBREVIATIONS: dict[str, str] = {
    # Core / Revised Core
    "Core Set": "Core",
    "Revised Core Set": "rCore",
    # Dunwich Legacy
    "The Dunwich Legacy": "TDL",
    "The Dunwich Legacy Investigator Expansion": "TDL IE",
    "The Dunwich Legacy Campaign Expansion": "TDL CE",
    # Path to Carcosa
    "The Path to Carcosa": "TPC",
    "The Path to Carcosa Investigator Expansion": "TPC IE",
    "The Path to Carcosa Campaign Expansion": "TPC CE",
    # Forgotten Age
    "The Forgotten Age": "TFA",
    "The Forgotten Age Investigator Expansion": "TFA IE",
    "The Forgotten Age Campaign Expansion": "TFA CE",
    # Circle Undone
    "The Circle Undone": "TCU",
    "The Circle Undone Investigator Expansion": "TCU IE",
    "The Circle Undone Campaign Expansion": "TCU CE",
    # Dream-Eaters
    "The Dream-Eaters": "TDE",
    "The Dream-Eaters Investigator Expansion": "TDE IE",
    "The Dream-Eaters Campaign Expansion": "TDE CE",
    # Innsmouth Conspiracy
    "The Innsmouth Conspiracy": "TIC",
    "The Innsmouth Conspiracy Investigator Expansion": "TIC IE",
    "The Innsmouth Conspiracy Campaign Expansion": "TIC CE",
    # Edge of the Earth
    "Edge of the Earth": "EotE",
    "Edge of the Earth Investigator Expansion": "EotE IE",
    "Edge of the Earth Campaign Expansion": "EotE CE",
    # Scarlet Keys
    "The Scarlet Keys": "TSK",
    "The Scarlet Keys Investigator Expansion": "TSK IE",
    "The Scarlet Keys Campaign Expansion": "TSK CE",
    # Feast of Hemlock Vale
    "The Feast of Hemlock Vale": "FHV",
    "The Feast of Hemlock Vale Investigator Expansion": "FHV IE",
    "The Feast of Hemlock Vale Campaign Expansion": "FHV CE",
    # Drowned City
    "The Drowned City": "TDC",
    "The Drowned City Investigator Expansion": "TDC IE",
    "The Drowned City Campaign Expansion": "TDC CE",
    # Side stories / promos
    "Return to the Night of the Zealot": "RtNZ",
    "Return to the Dunwich Legacy": "RtDL",
    "Return to the Path to Carcosa": "RtPC",
    "Return to the Forgotten Age": "RtFA",
    "Return to the Circle Undone": "RtCU",
    "Return to the Dream-Eaters": "RtDE",
    "Return to the Innsmouth Conspiracy": "RtIC",
    "Investigator Starter Decks": "Starter",
    "Nathaniel Cho": "Starter",
    "Harvey Walters": "Starter",
    "Winifred Habbamock": "Starter",
    "Jacqueline Fine": "Starter",
    "Stella Clark": "Starter",
    "Promo": "Promo",
    "Books": "Books",
}


def _abbrev_pack(pack_name: str) -> str:
    """Return community abbreviation for a pack name, or the original if unknown."""
    return PACK_ABBREVIATIONS.get(pack_name, pack_name)


def _get_cached_pack_list() -> list[dict]:
    global _pack_list_cache, _pack_list_cache_ts
    import time
    if _pack_list_cache and (time.monotonic() - _pack_list_cache_ts) < _PACK_LIST_TTL:
        return _pack_list_cache
    packs = get_card_packs()
    if packs:
        _pack_list_cache = packs
        _pack_list_cache_ts = time.monotonic()
    return _pack_list_cache


async def _fetch_all_cards(include_encounter: bool = False) -> list[dict]:
    """DB-first card list fetch with in-memory cache (TTL 10 min) and API fallback."""
    import time
    global _cards_cache, _cards_cache_ts, _cards_encounter_cache, _cards_encounter_cache_ts
    cache = _cards_encounter_cache if include_encounter else _cards_cache
    cache_ts = _cards_encounter_cache_ts if include_encounter else _cards_cache_ts
    if cache and (time.monotonic() - cache_ts) < _CARDS_CACHE_TTL:
        return cache
    from ..repositories.cards_repo import get_all_cards
    from ..clients.arkhamdb_client import fetch_all_cards_sync
    try:
        cards = await asyncio.to_thread(get_all_cards, include_encounter)
        if cards:
            if include_encounter:
                _cards_encounter_cache[:] = cards
                _cards_encounter_cache_ts = time.monotonic()
            else:
                _cards_cache[:] = cards
                _cards_cache_ts = time.monotonic()
            return cards
    except Exception as exc:
        logger.warning(f"DB get_all_cards failed: {exc}")
    logger.info("Falling back to ArkhamDB API for all cards")
    return await asyncio.to_thread(fetch_all_cards_sync, include_encounter)


async def _fetch_all_taboos() -> list[dict]:
    """DB-first taboo list fetch with API fallback."""
    from ..repositories.taboos_repo import get_all_taboos
    from ..clients.arkhamdb_client import fetch_taboos_sync
    try:
        taboos = await asyncio.to_thread(get_all_taboos)
        if taboos:
            return taboos
    except Exception as exc:
        logger.warning(f"DB get_all_taboos failed: {exc}")
    logger.info("Falling back to ArkhamDB API for taboos")
    return await asyncio.to_thread(fetch_taboos_sync)


async def _fetch_faq(card_code: str) -> list | None:
    """DB-first FAQ fetch with cache-on-demand. Refreshes if older than TTL."""
    from ..repositories.faq_repo import get_faq_by_code, upsert_faq
    from ..clients.arkhamdb_client import fetch_faq_by_card_code_sync
    from datetime import timezone
    cached, updated_at = None, None
    try:
        cached, updated_at = await asyncio.to_thread(get_faq_by_code, card_code)
    except Exception as exc:
        logger.warning(f"DB get_faq_by_code failed for {card_code}: {exc}")

    if cached is not None and updated_at:
        try:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).days
            if age_days < _FAQ_CACHE_TTL_DAYS:
                return cached
        except Exception:
            return cached

    logger.info(f"FAQ cache miss or stale for {card_code}, fetching from ArkhamDB")
    fresh = await asyncio.to_thread(fetch_faq_by_card_code_sync, card_code)
    if fresh is not None:
        try:
            await asyncio.to_thread(upsert_faq, card_code, fresh)
        except Exception as exc:
            logger.warning(f"faq_cache_save_failed {card_code}: {exc}")
    return fresh


async def _fetch_decklist_cached(decklist_id: str) -> dict:
    """Fetch decklist from DB cache (TTL 24h), falling back to ArkhamDB API and saving."""
    from ..clients.arkhamdb_client import fetch_decklist_sync
    from ..core.supabase_client import get_supabase_client
    from datetime import timezone as _tz
    client = get_supabase_client()
    if client:
        try:
            rows = client.get("arkham_decklists_cache", {
                "decklist_id": f"eq.{decklist_id}", "select": "raw,updated_at", "limit": "1"
            })
            if rows:
                updated_at = rows[0].get("updated_at", "")
                try:
                    age_hours = (datetime.now(_tz.utc) - datetime.fromisoformat(updated_at)).total_seconds() / 3600
                    if age_hours < _DECKLIST_CACHE_TTL_HOURS:
                        return rows[0]["raw"]
                except Exception:
                    return rows[0]["raw"]
        except Exception as exc:
            logger.warning("decklist_cache_read_failed: %s", exc)
    deck = await asyncio.to_thread(fetch_decklist_sync, decklist_id)
    if client and deck:
        try:
            client.upsert("arkham_decklists_cache", {"decklist_id": decklist_id, "raw": deck}, on_conflict="decklist_id")
        except Exception as exc:
            logger.warning("decklist_cache_write_failed: %s", exc)
    return deck


async def _check_rate_limit(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if is_admin_user(user_id):
        return True
    allowed, message = rate_limiter.check(user_id, chat_id)
    if not allowed:
        await update.message.reply_text(message)
    return allowed


def _chunks(text: str, size: int = 3900) -> list[str]:
    import re
    if len(text) <= size:
        return [text]

    def _split_para(para: str, limit: int) -> list[str]:
        """Split a single paragraph at sentence boundaries."""
        if len(para) <= limit:
            return [para]
        sentences = re.split(r'(?<=[.!?])\s+', para)
        parts, current = [], ""
        for sent in sentences:
            candidate = (current + " " + sent).strip() if current else sent
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    parts.append(current)
                if len(sent) > limit:
                    while sent:
                        cut = sent[:limit]
                        space = cut.rfind(' ')
                        if space > 0:
                            parts.append(sent[:space])
                            sent = sent[space + 1:]
                        else:
                            parts.append(cut)
                            sent = sent[limit:]
                    current = ""
                else:
                    current = sent
        if current:
            parts.append(current)
        return parts or [para[:limit]]

    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".lstrip("\n") if current else para
        if len(candidate) <= size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(para) > size:
                sub = _split_para(para, size)
                chunks.extend(sub[:-1])
                current = sub[-1]
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks or [""]


def _arkhamdb_html_to_telegram(html: str) -> str:
    """Convert ArkhamDB HTML to the subset supported by Telegram."""
    import re
    icon_map = {
        '': '[reação]', '': '[livre]', '': '[ação]',
        '': '[automático]', '': '[guardião]', '': '[sobrevivente]',
        '': '[investigador]', '': '[místico]', '': '[desonesto]',
        '®': '[reação]',
    }
    for char, replacement in icon_map.items():
        html = html.replace(char, replacement)
    html = re.sub(r'<img[^>]*>', '', html)
    html = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', html, flags=re.DOTALL)
    html = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', html, flags=re.DOTALL)
    html = re.sub(r'<del>(.*?)</del>', r'<s>\1</s>', html, flags=re.DOTALL)
    html = re.sub(r'<a href="/card/([^"]+)">', r'<a href="https://arkhamdb.com/card/\1">', html)
    html = re.sub(r'\s+<b>A:</b>', '\n\n<b>A:</b>', html)
    html = re.sub(r'<p>(.*?)</p>', r'\1\n\n', html, flags=re.DOTALL)
    html = re.sub(
        r'<ul>(.*?)</ul>',
        lambda m: '\n' + re.sub(r'<li>(.*?)</li>', r'\n\1', m.group(1), flags=re.DOTALL) + '\n',
        html, flags=re.DOTALL,
    )
    html = re.sub(
        r'<ol>(.*?)</ol>',
        lambda m: '\n' + re.sub(r'<li>(.*?)</li>', r'\n\1', m.group(1), flags=re.DOTALL) + '\n',
        html, flags=re.DOTALL,
    )
    html = re.sub(r'<(?!/?(?:b|i|s|u|code|pre|a)[\s>])[^>]+>', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()


def _format_uptime(now: datetime) -> str:
    seconds = max(0, int((now - BOT_STARTED_AT).total_seconds()))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _time_until_next_post(times: list, days: list, timezone_name: str) -> str:
    """Returns human-readable time until next scheduled post (PT-BR)."""
    from zoneinfo import ZoneInfo
    if not times:
        return "não agendado"
    day_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
    allowed_days = set(day_map[d] for d in (days or []) if d in day_map) or set(range(7))
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = UTC
    now = datetime.now(tz)
    for days_ahead in range(8):
        candidate_date = (now + timedelta(days=days_ahead)).date()
        if candidate_date.weekday() not in allowed_days:
            continue
        for time_str in sorted(times):
            try:
                h, m = map(int, time_str.split(':'))
            except Exception:
                continue
            candidate = datetime(candidate_date.year, candidate_date.month, candidate_date.day, h, m, tzinfo=tz)
            if candidate > now:
                diff = candidate - now
                total_mins = int(diff.total_seconds() / 60)
                hours, mins = divmod(total_mins, 60)
                if days_ahead == 0:
                    if hours > 0:
                        return f"hoje às {time_str} (em {hours}h {mins}m)"
                    return f"hoje às {time_str} (em {mins}m)"
                elif days_ahead == 1:
                    return f"amanhã às {time_str}"
                else:
                    return f"{candidate_date.strftime('%d/%m')} às {time_str}"
    return "não agendado"


def _as_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim", "on"}
    return bool(value)


def _safe_status_value(value) -> str:
    return escape(str(value if value not in (None, "") else "-"))


def _code(value) -> str:
    return f"<code>{_safe_status_value(value)}</code>"


def _day_labels(s: dict) -> dict:
    return {
        'mon': s['day_mon'], 'tue': s['day_tue'], 'wed': s['day_wed'],
        'thu': s['day_thu'], 'fri': s['day_fri'], 'sat': s['day_sat'],
        'sun': s['day_sun'], 'all': s['day_all'],
    }


async def _fetch_card_image(card_code: str, image_src: str | None = None) -> io.BytesIO | None:
    """Tries all extensions and returns a valid image BytesIO or None."""
    import httpx
    urls = []
    if image_src:
        urls.append(urljoin(BASE_URL, image_src))
    for ext in EXTENSIONS_TO_TRY:
        url = urljoin(BASE_URL, f"/bundles/cards/{card_code}{ext}")
        if url not in urls:
            urls.append(url)
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                continue
            raw = resp.content
            buf = io.BytesIO(raw)
            img = Image.open(buf)
            img.load()
            buf.seek(0)
            return buf
        except Exception:
            continue
    return None


def _spoiler_caption(card: dict) -> tuple[str, bool]:
    """Returns (caption, is_spoiler). If spoiler, wraps body in <tg-spoiler>."""
    from ..formatters.text_formatters import format_card_caption
    is_spoiler = bool(card.get('spoiler'))
    full_caption = format_card_caption(card, is_interactive=True)
    if not is_spoiler:
        return full_caption, False
    lines = full_caption.split('\n', 1)
    body = lines[1] if len(lines) > 1 else ''
    caption = f"{lines[0]}\n<tg-spoiler>{body}</tg-spoiler>" if body else lines[0]
    return caption, True


def _pop_search_prompt(context):
    """Returns the stored prompt message object and clears search prompt keys.
    Does NOT clear search_user_msg_id — that is kept until the card is sent."""
    prompt = context.user_data.pop("search_prompt_obj", None)
    context.user_data.pop("search_prompt_msg_id", None)
    context.user_data.pop("search_prompt_chat_id", None)
    context.user_data.pop("search_user_chat_id", None)
    return prompt
