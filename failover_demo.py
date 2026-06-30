import asyncio
from src.backends.base import Backend
from src.backends.resilient import ResilientBackend
from src.router import ComplexityRouter


class WorkingSmall(Backend):
    name = "gpt-oss-20b (mock)"
    async def predict(self, prompt): return "answer from the small model"


class BrokenLarge(Backend):
    name = "gpt-oss-120b (mock)"
    async def predict(self, prompt): raise RuntimeError("large backend is down")


async def main():
    small = ResilientBackend(WorkingSmall(), retries=0)
    large = ResilientBackend(BrokenLarge(), retries=0, failure_threshold=2, cooldown=30)
    router = ComplexityRouter(small=small, large=large, threshold=3)

    prompt = "Explain step by step why attention beats RNNs, and compare them."  # routes to large
    print("Complex prompts route to the LARGE model — which is down:\n")
    for i in range(1, 5):
        res = await router.complete("chat", prompt, {})
        print(f"  req {i}: served by {res.backend!r:22} failed_over={res.failed_over}  large.circuit={large.state}")
    print("\n-> Every request still got answered (by the small model). After 2 failures the")
    print("   large circuit OPENED, so reqs 3-4 failed over INSTANTLY (no waiting on a dead backend).")


if __name__ == "__main__":
    asyncio.run(main())
