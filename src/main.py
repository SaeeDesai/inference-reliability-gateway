from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from src.schemas import InferRequest, InferResponse
from src.backends.mock import MockBackend
from src.backends.groq import GroqBackend
from src.backends.resilient import ResilientBackend, CircuitOpenError
from src.cache import RedisCache

mock = MockBackend()
groq = GroqBackend(model="openai/gpt-oss-20b", name="gpt-oss-20b")
backend = ResilientBackend(groq, timeout=15, retries=2, backoff=0.5,
                           failure_threshold=3, cooldown=10)
cache = RedisCache()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await cache.ping()           # warn-only: Redis is optional
    except Exception:
        pass
    yield
    await groq.aclose()
    try:
        await cache.aclose()
    except Exception:
        pass

app = FastAPI(title="Inference Reliability Gateway", lifespan=lifespan)

@app.get("/health")
async def health():
    try:
        await cache.ping()
        redis_status = "up"
    except Exception:
        redis_status = "down"
    return {"status": "ok", "redis": redis_status}

@app.post("/v1/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    key = cache.make_key(request.task, request.input, request.options)

    # 1) Try cache (a cache error must NOT break the request -> treat as a miss)
    try:
        cached = await cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return InferResponse(output=cached, backend=backend.name, cached=True)

    # 2) Miss -> call the backend (with all of Week 1's resilience)
    try:
        output = await backend.predict(request.input)
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Backend unavailable (circuit open)")
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Backend timed out")
    except Exception:
        raise HTTPException(status_code=502, detail="Backend error")

    # 3) Store for next time (best-effort)
    try:
        await cache.set(key, output)
    except Exception:
        pass

    return InferResponse(output=output, backend=backend.name, cached=False)
