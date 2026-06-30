from fastapi import FastAPI
from src.schemas import InferRequest, InferResponse
from src.backends.mock import MockBackend

app = FastAPI(title="Inference Reliability Gateway")

backend = MockBackend()   # Day 1: one backend. Week 2: a router picks among many.

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    output = await backend.predict(request.input)
    return InferResponse(output=output, backend=backend.name)
