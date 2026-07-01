import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.schemas import InferRequest, InferResponse
from src.backends.groq import GroqBackend
from src.backends.resilient import ResilientBackend, CircuitOpenError
from src.cache import RedisCache
from src.ratelimit import RateLimiter, RateLimitExceeded
from src.router import ComplexityRouter
from src.metrics import REQUESTS, LATENCY, IN_FLIGHT

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

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


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/infer", response_model=InferResponse)
async def infer(body: InferRequest, req: Request, response: Response):
    request_id = uuid.uuid4().hex[:8]
    response.headers["X-Request-ID"] = request_id
    start = time.perf_counter()
    client_id = req.headers.get("x-client-id") or (req.client.host if req.client else "unknown")
    status, backend_name, cached, route = 200, None, False, None

    IN_FLIGHT.inc()
    try:
        try:
            await limiter.check(client_id)
        except RateLimitExceeded:
            status = 429
            raise HTTPException(status_code=429, detail="Too many requests")
        except Exception:
            pass

        key = cache.make_key(body.task, body.input, body.options)
        try:
            hit = await cache.get(key)
        except Exception:
            hit = None
        if hit is not None:
            backend_name, cached = "cache", True
            return InferResponse(output=hit, backend="cache", cached=True)

        try:
            result = await router.complete(body.task, body.input, body.options)
        except CircuitOpenError:
            status = 503
            raise HTTPException(status_code=503, detail="Backend unavailable (circuit open)")
        except TimeoutError:
            status = 504
            raise HTTPException(status_code=504, detail="Backend timed out")
        except Exception:
            status = 502
            raise HTTPException(status_code=502, detail="Backend error")

        backend_name, route = result.backend, result.route
        try:
            await cache.set(key, result.output)
        except Exception:
            pass

        return InferResponse(output=result.output, backend=result.backend,
                             cached=False, route=result.route)
    finally:
        latency = time.perf_counter() - start
        IN_FLIGHT.dec()
        label = backend_name or "none"
        LATENCY.labels(backend=label).observe(latency)
        REQUESTS.labels(backend=label, status=str(status), cached=str(cached).lower()).inc()
        logger.info(
            "infer",
            request_id=request_id, task=body.task, client=client_id,
            backend=backend_name, cached=cached, route=route,
            status=status, latency_ms=round(latency * 1000, 2),
        )
