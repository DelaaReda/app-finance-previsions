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


def test_daily_recommendations_preserves_forecast_fusion_attribution_contract(monkeypatch):
    class StubRecommendationsService:
        async def generate_daily_recommendations(self, **_kwargs):
            return {
                "recommendations": [
                    {
                        "ticker": "AAPL",
                        "action": "BUY",
                        "forecast_fusion": {
                            "blended_score": 0.78,
                            "dominant_layer": "forecast_confidence",
                            "layers": [
                                {
                                    "layer": "forecast_confidence",
                                    "weight": 0.30,
                                    "contribution": 0.234,
                                    "normalized_contribution": 0.31,
                                    "contribution_pct": 31.0,
                                    "layer_rank": 1,
                                },
                                {
                                    "layer": "momentum",
                                    "weight": 0.20,
                                    "contribution": 0.156,
                                    "normalized_contribution": 0.207,
                                    "contribution_pct": 20.7,
                                    "layer_rank": 2,
                                },
                            ],
                            "contribution_normalization": {
                                "scheme": "layer_contribution_share",
                                "sum": 1.0,
                            },
                            "stability": {
                                "status": "watch",
                                "dominance_gap": 0.103,
                                "dominant_share": 0.31,
                                "runner_up_layer": "momentum",
                                "runner_up_share": 0.207,
                            },
                            "attribution": {
                                "forecast_direction": "up",
                                "market_regime": "BULL_MARKET",
                                "expected_return": 0.123,
                                "news_sentiment": 0.65,
                                "macro_alignment": 0.9,
                            },
                        },
                    }
                ],
                "market_context": {"regime": "NORMAL", "summary": "stable", "key_drivers": []},
                "generated_at": "2026-03-10T00:00:00",
                "valid_until": "2026-03-11T00:00:00",
            }

    monkeypatch.setattr(recommendations_route, "RecommendationsService", StubRecommendationsService)

    client = _build_client()
    resp = client.get("/api/recommendations/daily?limit=1")
    assert resp.status_code == 200
    payload = resp.json()

    fusion = payload["data"]["recommendations"][0]["forecast_fusion"]
    assert fusion["dominant_layer"] == "forecast_confidence"
    assert fusion["contribution_normalization"] == {
        "scheme": "layer_contribution_share",
        "sum": 1.0,
    }
    assert fusion["stability"]["status"] == "watch"
    assert fusion["stability"]["runner_up_layer"] == "momentum"
    assert fusion["attribution"]["market_regime"] == "BULL_MARKET"
    assert fusion["layers"][0]["normalized_contribution"] == 0.31
    assert fusion["layers"][0]["layer_rank"] == 1


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
