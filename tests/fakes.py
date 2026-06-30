import asyncio
from src.backends.base import Backend

class SlowBackend(Backend):
    name = "slow"
    def __init__(self, delay: float):
        self.delay = delay
    async def predict(self, prompt: str) -> str:
        await asyncio.sleep(self.delay)
        return "ok"

class FailNTimes(Backend):
    """Fails its first N calls, then succeeds."""
    name = "flaky"
    def __init__(self, fail_first_n: int):
        self.fail_first_n = fail_first_n
        self.calls = 0
    async def predict(self, prompt: str) -> str:
        self.calls += 1
        if self.calls <= self.fail_first_n:
            raise RuntimeError(f"boom (call {self.calls})")
        return f"ok (call {self.calls})"
