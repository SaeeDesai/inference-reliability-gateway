import asyncio
import time
import httpx

URL = "http://localhost:8000/v1/infer"

async def main():
    # Unique suffix guarantees the FIRST call is a cold miss (real model call).
    payload = {"task": "chat",
               "input": f"In one sentence, what is an API gateway? (run {int(time.time())})"}
    async with httpx.AsyncClient(timeout=30) as client:
        async def call():
            t = time.perf_counter()
            r = await client.post(URL, json=payload)
            return time.perf_counter() - t, r.json()["cached"]
        d1, c1 = await call()   # cold: hits the real model
        d2, c2 = await call()   # warm: served from Redis
        print(f"cold call: {d1*1000:8.1f} ms   cached={c1}")
        print(f"warm call: {d2*1000:8.1f} ms   cached={c2}")
        print(f"speedup  : {d1/d2:6.0f}x")

if __name__ == "__main__":
    asyncio.run(main())
