import time
from collections import defaultdict, deque

from .config import (
    PUBLIC_COMMANDS_RATE_LIMIT_ENABLED,
    RATE_LIMIT_EXCEEDED_MESSAGE_EN,
    RATE_LIMIT_PER_CHAT_MAX_REQUESTS,
    RATE_LIMIT_PER_CHAT_WINDOW_SECONDS,
    RATE_LIMIT_PER_USER_MAX_REQUESTS,
    RATE_LIMIT_PER_USER_WINDOW_SECONDS,
)


class InMemoryRateLimiter:
    # Every N checks, drop buckets whose window has fully expired. Without this the
    # defaultdicts grow one entry per distinct user/chat ever seen and never shrink,
    # since _trim() materialises an empty deque for every key it inspects.
    _SWEEP_EVERY_CHECKS = 256

    def __init__(self):
        self._user_hits = defaultdict(deque)
        self._chat_hits = defaultdict(deque)
        self._checks_since_sweep = 0

    @staticmethod
    def _trim(bucket, key: int, window_seconds: int, now: float) -> deque:
        hits = bucket[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        return hits

    @staticmethod
    def _is_allowed(hits: deque, max_requests: int) -> bool:
        return len(hits) < max_requests

    def _sweep_expired(self, now: float) -> None:
        """Remove buckets with no hit inside their window, bounding memory for one-off users."""
        for bucket, window_seconds in (
            (self._user_hits, RATE_LIMIT_PER_USER_WINDOW_SECONDS),
            (self._chat_hits, RATE_LIMIT_PER_CHAT_WINDOW_SECONDS),
        ):
            stale = [key for key, hits in bucket.items() if not hits or now - hits[-1] > window_seconds]
            for key in stale:
                del bucket[key]

    def check(self, user_id: int, chat_id: int, now: float | None = None) -> tuple[bool, str | None]:
        if not PUBLIC_COMMANDS_RATE_LIMIT_ENABLED:
            return True, None
        now = time.time() if now is None else now
        self._checks_since_sweep += 1
        if self._checks_since_sweep >= self._SWEEP_EVERY_CHECKS:
            self._checks_since_sweep = 0
            self._sweep_expired(now)
        user_hits = self._trim(self._user_hits, user_id, RATE_LIMIT_PER_USER_WINDOW_SECONDS, now)
        chat_hits = self._trim(self._chat_hits, chat_id, RATE_LIMIT_PER_CHAT_WINDOW_SECONDS, now)
        # Check both BEFORE recording — prevents user hit being counted on chat rejection
        if not self._is_allowed(user_hits, RATE_LIMIT_PER_USER_MAX_REQUESTS):
            return False, RATE_LIMIT_EXCEEDED_MESSAGE_EN
        if not self._is_allowed(chat_hits, RATE_LIMIT_PER_CHAT_MAX_REQUESTS):
            return False, RATE_LIMIT_EXCEEDED_MESSAGE_EN
        user_hits.append(now)
        chat_hits.append(now)
        return True, None


rate_limiter = InMemoryRateLimiter()
