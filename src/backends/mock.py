import asyncio
from src.backends.base import Backend

class MockBackend(Backend):
    name = "mock"

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    async def predict(self, prompt: str) -> str:
        if self.delay:
            await asyncio.sleep(self.delay)   # pretend the kitchen is cooking
        return f"[mock] you said: {prompt}"
