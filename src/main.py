from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.schemas import InferRequest, InferResponse
from src.backends.mock import MockBackend
from src.backends.groq import GroqBackend

mock = MockBackend()
groq = GroqBackend(model="openai/gpt-oss-20b", name="gpt-oss-20b")

backend = groq   # Day 2: real backend active. Week 2: a router picks among many.

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield                    # <- app runs while paused here
    await groq.aclose()      # <- runs on shutdown: clean up the HTTP client

app = FastAPI(title="Inference Reliability Gateway", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    output = await backend.predict(request.input)
    return InferResponse(output=output, backend=backend.name)
