import hashlib
import json
import redis.asyncio as redis
from src.config import REDIS_URL


class RedisCache:
    """Caches responses in Redis, keyed by a hash of the normalized request."""

    def __init__(self, url: str = REDIS_URL, ttl: int = 3600):
        # from_url is lazy: no connection until the first command.
        self.client = redis.from_url(url, decode_responses=True)
        self.ttl = ttl   # entries auto-expire after this many seconds (TTL)

    @staticmethod
    def make_key(task: str, text: str, options: dict) -> str:
        # Normalize lightly (task case + whitespace) but NOT the prompt text itself.
        payload = json.dumps(
            {"task": task.strip().lower(), "input": text.strip(), "options": options or {}},
            sort_keys=True,
        )
        return "cache:" + hashlib.sha256(payload.encode()).hexdigest()

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str) -> None:
        await self.client.set(key, value, ex=self.ttl)   # ex = TTL in seconds

    async def ping(self) -> bool:
        return await self.client.ping()

    async def aclose(self) -> None:
        await self.client.aclose()
