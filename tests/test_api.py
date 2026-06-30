from fastapi.testclient import TestClient
from src.main import app
from src.backends.mock import MockBackend


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_infer_returns_backend_output(monkeypatch):
    monkeypatch.setattr("src.main.backend", MockBackend())   # swap Groq for the mock
    with TestClient(app) as client:
        r = client.post("/v1/infer", json={"task": "chat", "input": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["output"] == "[mock] you said: hello"
    assert body["backend"] == "mock"


def test_infer_rejects_invalid_request():
    with TestClient(app) as client:
        r = client.post("/v1/infer", json={"task": "chat"})   # missing 'input'
    assert r.status_code == 422                                 # Pydantic validation
