import asyncio
import time
from src.backends.base import Backend
from src.backends.resilient import ResilientBackend, CircuitOpenError


class SlowBackend(Backend):
    name = "slow"
    def __init__(self, delay): self.delay = delay
    async def predict(self, prompt):
        await asyncio.sleep(self.delay)
        return "ok"


class FailNTimes(Backend):
    name = "flaky"
    def __init__(self, fail_first_n): self.fail_first_n = fail_first_n; self.calls = 0
    async def predict(self, prompt):
        self.calls += 1
        if self.calls <= self.fail_first_n:
            raise RuntimeError(f"boom (call {self.calls})")
        return f"ok (call {self.calls})"


async def main():
    print("\n=== 1) TIMEOUT: backend takes 2.0s, we allow 0.5s ===")
    g = ResilientBackend(SlowBackend(2.0), timeout=0.5, retries=0)
    t = time.perf_counter()
    try:
        await g.predict("hi")
    except TimeoutError:
        print(f"  gave up after {time.perf_counter()-t:.2f}s instead of hanging 2.0s")

    print("\n=== 2) RETRY: backend fails once, then works ===")
    fb = FailNTimes(fail_first_n=1)
    g = ResilientBackend(fb, timeout=1, retries=2, backoff=0.2)
    out = await g.predict("hi")
    print(f"  recovered -> {out!r}; backend was called {fb.calls} times")

    print("\n=== 3) CIRCUIT BREAKER: backend down, then recovers ===")
    fb = FailNTimes(fail_first_n=3)
    cb = ResilientBackend(fb, timeout=1, retries=0, failure_threshold=3, cooldown=1.0)

    async def hit(i):
        try:
            out = await cb.predict("hi"); print(f"  req {i}: OK -> {out!r}  [{cb.state}]")
        except CircuitOpenError:
            print(f"  req {i}: FAST-FAIL, backend NOT called  [{cb.state}]")
        except Exception as e:
            print(f"  req {i}: FAIL -> {e}  [{cb.state}]")

    for i in range(1, 4): await hit(i)     # 3 failures -> opens
    for i in range(4, 7): await hit(i)     # open -> fast-fail, backend shielded
    print("  ...waiting out the cooldown...")
    await asyncio.sleep(1.1)
    for i in range(7, 9): await hit(i)     # half-open trial -> recovers, closes
    print(f"  >> backend was called only {fb.calls} times across 8 requests")


if __name__ == "__main__":
    asyncio.run(main())
