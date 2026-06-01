import os
import time

from ..core.supabase_client import get_supabase_client

_cache: dict = {}
_cache_ts: float = 0.0
_CACHE_TTL = float(os.getenv("SETTINGS_CACHE_TTL_SECONDS", "10"))


def _invalidate_cache() -> None:
    global _cache_ts
    _cache_ts = 0.0


def get_all_settings() -> dict:
    # Always hand callers a shallow copy so mutating the result can't corrupt the
    # shared cache (and a later get_setting won't see another caller's edits).
    global _cache, _cache_ts
    if _cache and (time.monotonic() - _cache_ts) < _CACHE_TTL:
        return dict(_cache)
    client = get_supabase_client()
    if not client:
        return dict(_cache)  # return stale cache if DB unavailable
    rows = client.get("bot_settings")
    _cache = {row["key"]: row["value"] for row in rows}
    _cache_ts = time.monotonic()
    return dict(_cache)


def get_setting(key: str, default=None):
    return get_all_settings().get(key, default)


def set_setting(key: str, value, description: str | None = None, updated_by: str | None = None) -> None:
    client = get_supabase_client()
    if not client:
        return
    payload = {"key": key, "value": value, "updated_by": updated_by}
    if description is not None:
        payload["description"] = description
    client.upsert("bot_settings", payload, on_conflict="key")
    _invalidate_cache()
