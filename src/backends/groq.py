import httpx
from src.backends.base import Backend
from src.config import GROQ_API_KEY, GROQ_BASE_URL

class GroqBackend(Backend):
    """A real model backend that fits the exact same Backend shape as MockBackend."""

    def __init__(self, model: str, name: str | None = None, timeout: float = 30.0):
        # Fail LOUDLY now if the key is missing, instead of a confusing error mid-request.
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")

        self.model = model
        self.name = name or model

        # ONE reusable async client = connection pooling (reuse the TCP connection
        # instead of re-dialing every call). Created once, used for every request.
        self.client = httpx.AsyncClient(
            base_url=GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=timeout,
        )

    async def predict(self, prompt: str) -> str:
        # 'await' = pause here while we wait on the network, let other requests run.
        resp = await self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()                       # turn HTTP errors into exceptions
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def aclose(self) -> None:
        await self.client.aclose()                    # close the connection pool cleanly
