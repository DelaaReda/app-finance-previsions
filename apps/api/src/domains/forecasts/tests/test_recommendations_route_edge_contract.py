from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.forecasts.api import recommendations as recommendations_route


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(recommendations_route.router, prefix="/api/recommendations")
    return TestClient(app)


def test_daily_recommendations_returns_edge_ok_payload(monkeypatch):
    class StubRecommendationsService:
        async def generate_daily_recommendations(self, **_kwargs):
            return {
                "recommendations": [{"ticker": "AAPL", "action": "BUY"}],
                "market_context": {"regime": "NORMAL", "summary": "stable", "key_drivers": []},
                "generated_at": "2026-03-10T00:00:00",
                "valid_until": "2026-03-11T00:00:00",
            }

    monkeypatch.setattr(recommendations_route, "RecommendationsService", StubRecommendationsService)

    client = _build_client()
    resp = client.get("/api/recommendations/daily?limit=1")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["meta"]["source"] == ["recommendations_daily", "weekly_brief_snapshot"]
    assert payload["meta"]["fallback"] is False
    assert payload["data"]["recommendations"][0]["ticker"] == "AAPL"


def test_daily_recommendations_returns_edge_degraded_payload(monkeypatch):
    class BrokenRecommendationsService:
        async def generate_daily_recommendations(self, **_kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(recommendations_route, "RecommendationsService", BrokenRecommendationsService)

    client = _build_client()
    resp = client.get("/api/recommendations/daily?limit=1")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert payload["error"]["code"] == "recommendations_unavailable"
    assert payload["meta"]["source"] == ["recommendations_daily", "critical_error_fallback"]
    assert payload["meta"]["fallback"] is True
    assert payload["data"]["recommendations"] == []
