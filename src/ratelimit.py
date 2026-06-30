import redis.asyncio as redis
from src.config import REDIS_URL


class RateLimitExceeded(Exception):
    """Raised when a client goes over the allowed rate."""


class RateLimiter:
    """Fixed-window rate limiter using Redis atomic INCR."""

    def __init__(self, url: str = REDIS_URL, limit: int = 5, window: int = 10):
        self.client = redis.from_url(url, decode_responses=True)
        self.limit = limit       # max requests...
        self.window = window     # ...per this many seconds

    async def check(self, client_id: str) -> None:
        key = f"ratelimit:{client_id}"
        count = await self.client.incr(key)          # atomic +1 (creates key at 1)
        if count == 1:
            await self.client.expire(key, self.window)  # start the window's clock
        if count > self.limit:
            raise RateLimitExceeded(f"{self.limit}/{self.window}s exceeded")

    async def ping(self) -> bool:
        return await self.client.ping()

    async def aclose(self) -> None:
        await self.client.aclose()
