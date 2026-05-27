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
    def __init__(self):
        self._user_hits = defaultdict(deque)
        self._chat_hits = defaultdict(deque)

    @staticmethod
    def _allow(bucket, key: int, max_requests: int, window_seconds: int, now: float) -> bool:
        hits = bucket[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= max_requests:
            return False
        hits.append(now)
        return True

    def allow_user(self, user_id: int, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self._allow(self._user_hits, user_id, RATE_LIMIT_PER_USER_MAX_REQUESTS, RATE_LIMIT_PER_USER_WINDOW_SECONDS, now)

    def allow_chat(self, chat_id: int, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self._allow(self._chat_hits, chat_id, RATE_LIMIT_PER_CHAT_MAX_REQUESTS, RATE_LIMIT_PER_CHAT_WINDOW_SECONDS, now)

    def check(self, user_id: int, chat_id: int, now: float | None = None) -> tuple[bool, str | None]:
        if not PUBLIC_COMMANDS_RATE_LIMIT_ENABLED:
            return True, None
        now = time.time() if now is None else now
        if not self.allow_user(user_id, now):
            return False, RATE_LIMIT_EXCEEDED_MESSAGE_EN
        if not self.allow_chat(chat_id, now):
            return False, RATE_LIMIT_EXCEEDED_MESSAGE_EN
        return True, None


rate_limiter = InMemoryRateLimiter()
