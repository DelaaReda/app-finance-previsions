from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import copilot as copilot_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(copilot_route.router)
    return TestClient(app)


def test_copilot_ask_route_delegates_to_service(monkeypatch):
    captured = {}

    async def fake_build_ask_payload(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "delegated",
            "sources": [],
            "citations": [],
            "model": "test-model",
            "confidence": 0.7,
            "generated_at": "2026-02-27T00:00:00Z",
            "sources_count": 0,
            "quality_status": "insufficient_sources",
            "requirements_met": {"min_sources_2": False, "quality_threshold": True},
        }

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_ask_payload",
        fake_build_ask_payload,
    )

    client = _client()
    resp = client.post(
        "/copilot/ask",
        json={
            "question": "What about AAPL?",
            "context_years": 3,
            "tickers": ["aapl"],
            "max_sources": 4,
            "scope": {"horizon": "1w"},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["answer"] == "delegated"
    assert captured["question"] == "What about AAPL?"
    assert captured["context_years"] == 3
    assert captured["tickers"] == ["aapl"]
    assert captured["max_sources"] == 4
    assert captured["scope"] == {"horizon": "1w"}


def test_copilot_history_route_delegates_to_service(monkeypatch):
    def fake_build_history_payload(*, limit: int):
        return {"conversations": [], "count": 0, "limit": limit, "source": ["test"]}

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_history_payload",
        fake_build_history_payload,
    )

    client = _client()
    resp = client.get("/copilot/history?limit=7")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["limit"] == 7
    assert payload["data"]["source"] == ["test"]


def test_copilot_context_route_delegates_to_service(monkeypatch):
    async def fake_build_context_payload(context_service_cls=None):
        return {"regime": "RISK_ON"}

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_context_payload",
        fake_build_context_payload,
    )

    client = _client()
    resp = client.get("/copilot/context")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["regime"] == "RISK_ON"
