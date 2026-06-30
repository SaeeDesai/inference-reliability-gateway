import asyncio
import time
from src.backends.mock import MockBackend

N = 20          # how many requests we fire at once
DELAY = 0.5     # each backend call "takes" half a second

async def fire(backend):
    start = time.perf_counter()
    # gather = start all N requests, then wait for them together
    await asyncio.gather(*[backend.predict("ping") for _ in range(N)])
    return time.perf_counter() - start

async def main():
    good = MockBackend(delay=DELAY)               # awaits properly (like httpx)
    bad  = MockBackend(delay=DELAY, block=True)   # blocks the loop (like requests)

    t_good = await fire(good)
    t_bad  = await fire(bad)

    print(f"\n{N} concurrent requests, each a {DELAY}s backend call:\n")
    print(f"  async (await)        : {t_good:5.2f}s   -> {N/t_good:5.1f} req/s")
    print(f"  blocking (time.sleep): {t_bad:5.2f}s   -> {N/t_bad:5.1f} req/s")
    print(f"\n  speedup: {t_bad/t_good:.1f}x when the event loop isn't blocked\n")

if __name__ == "__main__":
    asyncio.run(main())
