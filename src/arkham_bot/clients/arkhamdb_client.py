import logging
import time

import httpx
import requests
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential, AsyncRetrying

from .arkhamdb_models import (
    ArkhamDBHTTPError,
    validate_card_payload,
    validate_cards_payload,
    validate_decklist_payload,
    validate_factions_payload,
    validate_faq_payload,
    validate_packs_payload,
    validate_taboos_payload,
)
from ..core.config import (
    ARKHAM_CARD_API_URL,
    ARKHAMDB_API_URL,
    BASE_URL,
    INITIAL_BACKOFF,
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
)


logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'ArkhamDailyCardBot/1.0'
})
RETRYABLE_NETWORK_EXCEPTIONS = (
    requests.exceptions.ConnectionError, requests.exceptions.Timeout,
    requests.exceptions.RequestException
)
INTERACTIVE_IMAGE_RETRIES = 2
INTERACTIVE_IMAGE_TIMEOUT_SECONDS = min(REQUEST_TIMEOUT_SECONDS, 6)
_ASYNC_CLIENT: httpx.AsyncClient | None = None
_IMAGE_CACHE_TTL_SECONDS = 3600.0
_IMAGE_CACHE_MAX_ITEMS = 256
_image_cache: dict[str, tuple[float, bytes]] = {}


def _get_async_client(timeout: float | None = None) -> httpx.AsyncClient:
    global _ASYNC_CLIENT
    effective_timeout = timeout if timeout is not None else REQUEST_TIMEOUT_SECONDS
    if _ASYNC_CLIENT is None or _ASYNC_CLIENT.is_closed:
        _ASYNC_CLIENT = httpx.AsyncClient(
            timeout=effective_timeout,
            headers={"User-Agent": "ArkhamDailyCardBot/1.0"},
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _ASYNC_CLIENT


def _get_cached_image(url: str) -> bytes | None:
    cached = _image_cache.get(url)
    if not cached:
        return None
    ts, content = cached
    if time.monotonic() - ts > _IMAGE_CACHE_TTL_SECONDS:
        _image_cache.pop(url, None)
        return None
    return content


def _cache_image(url: str, content: bytes) -> None:
    if len(_image_cache) >= _IMAGE_CACHE_MAX_ITEMS:
        oldest = min(_image_cache, key=lambda key: _image_cache[key][0])
        _image_cache.pop(oldest, None)
    _image_cache[url] = (time.monotonic(), content)


def is_retryable_http_error(exception):
    """Checks if the HTTP error is a server code (5xx) or Rate Limit (429)."""
    if isinstance(exception, requests.exceptions.HTTPError):
        return exception.response.status_code in (429, 500, 502, 503, 504)
    return False


network_retry_sync = retry(
    wait=wait_exponential(multiplier=INITIAL_BACKOFF, min=2, max=30),
    stop=stop_after_attempt(MAX_RETRIES),
    retry=retry_if_exception_type(RETRYABLE_NETWORK_EXCEPTIONS) | retry_if_exception(is_retryable_http_error),
    before_sleep=lambda retry_state: logger.warning(
        f"Network attempt {retry_state.attempt_number} failed. "
        f"Retrying in {int(retry_state.next_action.sleep)}s..."
    )
)


def _parse_json_response(response, context: str):
    try:
        return response.json()
    except ValueError as exc:
        raise ArkhamDBHTTPError(f"Invalid JSON from ArkhamDB for {context}.") from exc


def _request_json_sync(url: str, context: str):
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _parse_json_response(response, context)


def _cards_url(include_encounter: bool = False) -> str:
    return f"{ARKHAMDB_API_URL}?encounter=1" if include_encounter else ARKHAMDB_API_URL


def _card_url(card_code: str) -> str:
    return f"{ARKHAM_CARD_API_URL}{card_code}"


def _faq_url(card_code: str) -> str:
    return f"{BASE_URL}api/public/faq/{card_code}"


def _packs_url() -> str:
    return f"{BASE_URL}api/public/packs/"


def _factions_url() -> str:
    return f"{BASE_URL}api/public/factions/"


def _taboos_url() -> str:
    return f"{BASE_URL}api/public/taboos/"


def _decklist_url(decklist_id: str) -> str:
    return f"{BASE_URL}api/public/decklist/{decklist_id}"


async def _request_json_async(url: str, context: str):
    client = _get_async_client()
    response = await client.get(url)
    response.raise_for_status()
    return _parse_json_response(response, context)


@network_retry_sync
def fetch_packs_sync() -> list[dict]:
    return validate_packs_payload(_request_json_sync(_packs_url(), "packs"), "packs")


@network_retry_sync
def fetch_factions_sync() -> list[dict]:
    return validate_factions_payload(_request_json_sync(_factions_url(), "factions"), "factions")


@network_retry_sync
def fetch_all_cards_sync(include_encounter: bool = False) -> list[dict]:
    return validate_cards_payload(_request_json_sync(_cards_url(include_encounter), "cards"), "cards")


@network_retry_sync
def fetch_card_by_code_sync(card_code: str) -> dict:
    payload = _request_json_sync(_card_url(card_code), f"card {card_code}")
    if isinstance(payload, list):
        if not payload:
            raise ArkhamDBHTTPError(f"ArkhamDB returned an empty card list for {card_code}.")
        payload = payload[0]
    return validate_card_payload(payload, f"card {card_code}")


@network_retry_sync
def fetch_faq_by_card_code_sync(card_code: str) -> dict | list | None:
    return validate_faq_payload(_request_json_sync(_faq_url(card_code), f"faq {card_code}"), f"faq {card_code}")


@network_retry_sync
def fetch_taboos_sync() -> list[dict] | dict:
    return validate_taboos_payload(_request_json_sync(_taboos_url(), "taboos"), "taboos")


@network_retry_sync
def fetch_decklist_sync(decklist_id: str) -> dict:
    return validate_decklist_payload(_request_json_sync(_decklist_url(decklist_id), f"decklist {decklist_id}"), f"decklist {decklist_id}")


async def fetch_card_by_code_async(card_code: str) -> dict:
    payload = await _request_json_async(_card_url(card_code), f"card {card_code}")
    if isinstance(payload, list):
        if not payload:
            raise ArkhamDBHTTPError(f"ArkhamDB returned an empty card list for {card_code}.")
        payload = payload[0]
    return validate_card_payload(payload, f"card {card_code}")


@network_retry_sync
def download_image_sync(url):
    """Downloads an image with retry (CRON Mode)."""
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.content


async def download_image_async(url):
    """Downloads an image asynchronously with retry (Interactive Mode)."""
    cached = _get_cached_image(url)
    if cached is not None:
        return cached
    async for attempt in AsyncRetrying(
        wait=wait_exponential(multiplier=1, min=1, max=3),
        stop=stop_after_attempt(INTERACTIVE_IMAGE_RETRIES),
        reraise=True,
    ):
        with attempt:
            client = _get_async_client(INTERACTIVE_IMAGE_TIMEOUT_SECONDS)
            response = await client.get(url, timeout=INTERACTIVE_IMAGE_TIMEOUT_SECONDS)
            response.raise_for_status()
            _cache_image(url, response.content)
            return response.content
