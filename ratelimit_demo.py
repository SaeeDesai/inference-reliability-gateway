import asyncio
import httpx

URL = "http://localhost:8000/v1/infer"
HEADERS = {"X-Client-Id": "demo-client"}          # all requests = same client/bucket
PAYLOAD = {"task": "chat", "input": "ping for the rate-limit demo"}

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(1, 9):                      # limit is 5 / 10s
            r = await client.post(URL, json=PAYLOAD, headers=HEADERS)
            tag = "OK" if r.status_code == 200 else "RATE-LIMITED (429)"
            print(f"request {i}: {r.status_code} {tag}")

if __name__ == "__main__":
    asyncio.run(main())
