import asyncio
import time
from src.backends.base import Backend

class MockBackend(Backend):
    name = "mock"

    def __init__(self, delay: float = 0.0, block: bool = False):
        self.delay = delay
        self.block = block   # True = simulate a BLOCKING call (the mistake)

    async def predict(self, prompt: str) -> str:
        if self.delay:
            if self.block:
                time.sleep(self.delay)            # WRONG: freezes the event loop
            else:
                await asyncio.sleep(self.delay)   # RIGHT: yields to the loop
        return f"[mock] you said: {prompt}"
