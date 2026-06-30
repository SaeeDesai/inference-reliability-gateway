import asyncio
import time
import textwrap
import httpx

URL = "http://localhost:8000/v1/infer"
HEADERS = {"X-Client-Id": f"routing-{int(time.time())}"}   # fresh bucket, dodge rate limit

PROMPTS = [
    "hi",
    "What is the capital of France?",
    "Explain step by step why transformers use self-attention, and compare it to RNNs.",
    "Summarize the plot of a generic detective novel in two sentences.",
    "Debug this: def add(a, b): retur a + b   # why does it error?",
]

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        for p in PROMPTS:
            r = await client.post(URL, json={"task": "chat", "input": p}, headers=HEADERS)
            b = r.json()
            print(f"\nPROMPT : {textwrap.shorten(p, 64)}")
            print(f"  -> backend = {b['backend']}")
            print(f"  -> route   = {b['route']}")

if __name__ == "__main__":
    asyncio.run(main())
