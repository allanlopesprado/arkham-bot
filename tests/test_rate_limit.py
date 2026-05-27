from arkham_bot.core.rate_limiter import InMemoryRateLimiter
from arkham_bot.core.config import RATE_LIMIT_PER_USER_MAX_REQUESTS, RATE_LIMIT_PER_CHAT_MAX_REQUESTS


def test_rate_limiter_blocks_user_after_limit():
    limiter = InMemoryRateLimiter()
    now = 1000.0
    for _ in range(RATE_LIMIT_PER_USER_MAX_REQUESTS):
        allowed, _ = limiter.check(user_id=1, chat_id=100, now=now)
        assert allowed is True
    allowed, message = limiter.check(user_id=1, chat_id=100, now=now)
    assert allowed is False
    assert message


def test_rate_limiter_blocks_chat_after_limit_with_different_users():
    limiter = InMemoryRateLimiter()
    now = 2000.0
    for user_id in range(RATE_LIMIT_PER_CHAT_MAX_REQUESTS):
        allowed, _ = limiter.check(user_id=user_id + 1, chat_id=999, now=now)
        assert allowed is True
    allowed, message = limiter.check(user_id=10000, chat_id=999, now=now)
    assert allowed is False
    assert message


def test_rate_limiter_window_expires():
    limiter = InMemoryRateLimiter()
    for _ in range(RATE_LIMIT_PER_USER_MAX_REQUESTS):
        assert limiter.check(user_id=2, chat_id=200, now=0.0)[0]
    assert limiter.check(user_id=2, chat_id=200, now=0.0)[0] is False
    assert limiter.check(user_id=2, chat_id=200, now=61.0)[0] is True
