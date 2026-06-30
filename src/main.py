from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from src.schemas import InferRequest, InferResponse
from src.backends.groq import GroqBackend
from src.backends.resilient import ResilientBackend, CircuitOpenError
from src.cache import RedisCache
from src.ratelimit import RateLimiter, RateLimitExceeded
from src.router import ComplexityRouter

# Two real backends: cheap/fast small, pricier/slower large — each wrapped in resilience.
groq_small = GroqBackend(model="openai/gpt-oss-20b", name="gpt-oss-20b")
groq_large = GroqBackend(model="openai/gpt-oss-120b", name="gpt-oss-120b")
small = ResilientBackend(groq_small, timeout=15, retries=2, failure_threshold=3, cooldown=10)
large = ResilientBackend(groq_large, timeout=30, retries=2, failure_threshold=3, cooldown=10)

router = ComplexityRouter(small=small, large=large, threshold=3)
cache = RedisCache()
limiter = RateLimiter(limit=5, window=10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for closeable in (groq_small, groq_large, cache, limiter):
        try:
            await closeable.aclose()
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
async def infer(body: InferRequest, req: Request):
    client_id = req.headers.get("x-client-id") or (req.client.host if req.client else "unknown")

    try:
        await limiter.check(client_id)
    except RateLimitExceeded:
        raise HTTPException(status_code=429, detail="Too many requests")
    except Exception:
        pass

    key = cache.make_key(body.task, body.input, body.options)
    try:
        cached = await cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return InferResponse(output=cached, backend="cache", cached=True)

    try:
        result = await router.complete(body.task, body.input, body.options)
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Backend unavailable (circuit open)")
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Backend timed out")
    except Exception:
        raise HTTPException(status_code=502, detail="Backend error")

    try:
        await cache.set(key, result.output)
    except Exception:
        pass

    return InferResponse(output=result.output, backend=result.backend,
                         cached=False, route=result.route)
