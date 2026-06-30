from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from src.schemas import InferRequest, InferResponse
from src.backends.mock import MockBackend
from src.backends.groq import GroqBackend
from src.backends.resilient import ResilientBackend, CircuitOpenError

mock = MockBackend()
groq = GroqBackend(model="openai/gpt-oss-20b", name="gpt-oss-20b")

# Wrap the real backend in resilience. Week 2 will wrap each routed backend the same way.
backend = ResilientBackend(groq, timeout=15, retries=2, backoff=0.5,
                           failure_threshold=3, cooldown=10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await groq.aclose()

app = FastAPI(title="Inference Reliability Gateway", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    try:
        output = await backend.predict(request.input)
    except CircuitOpenError:
        raise HTTPException(status_code=503, detail="Backend unavailable (circuit open)")
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Backend timed out")
    except Exception:
        raise HTTPException(status_code=502, detail="Backend error")
    return InferResponse(output=output, backend=backend.name)
