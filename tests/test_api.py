from fastapi.testclient import TestClient
from src.main import app
from src.router import RouteResult


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "redis" in body


def test_infer_routes_and_returns_output(monkeypatch):
    # Fake router so we don't call a real model
    class FakeRouter:
        async def complete(self, task, text, options):
            return RouteResult(output=f"[mock] you said: {text}",
                               backend="mock", route="small (test)")
    monkeypatch.setattr("src.main.router", FakeRouter())

    # Disable rate limiting
    async def _no_limit(client_id):
        return None
    monkeypatch.setattr("src.main.limiter.check", _no_limit)

    # Force a cache MISS so the router actually runs (isolate from real Redis)
    async def _miss(key):
        return None
    async def _noop_set(key, value):
        return None
    monkeypatch.setattr("src.main.cache.get", _miss)
    monkeypatch.setattr("src.main.cache.set", _noop_set)

    with TestClient(app) as client:
        r = client.post("/v1/infer", json={"task": "chat", "input": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["output"] == "[mock] you said: hello"
    assert body["backend"] == "mock"


def test_infer_rejects_invalid_request():
    with TestClient(app) as client:
        r = client.post("/v1/infer", json={"task": "chat"})
    assert r.status_code == 422
