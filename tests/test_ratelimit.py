import pytest
from src.ratelimit import RateLimiter, RateLimitExceeded


class _FakeRedis:
    """In-memory stand-in so the limiter logic is testable without Redis."""
    def __init__(self):
        self.store = {}
    async def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]
    async def expire(self, key, secs):
        return True


async def test_allows_then_blocks():
    rl = RateLimiter(limit=3, window=10)
    rl.client = _FakeRedis()
    for _ in range(3):
        await rl.check("c1")
    with pytest.raises(RateLimitExceeded):
        await rl.check("c1")


async def test_per_client_buckets():
    rl = RateLimiter(limit=1, window=10)
    rl.client = _FakeRedis()
    await rl.check("a")
    await rl.check("b")          # different client -> own bucket
    with pytest.raises(RateLimitExceeded):
        await rl.check("a")
