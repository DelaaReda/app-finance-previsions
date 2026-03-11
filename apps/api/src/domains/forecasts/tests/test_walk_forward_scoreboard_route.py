from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import forecasts as forecasts_route

FRESH_TS = "2099-02-27T00:00:00Z"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(forecasts_route.router)
    return TestClient(app)


def test_walk_forward_scoreboard_contract_and_cache(monkeypatch):
    forecasts_route.forecasts_service._FORECASTS_SCOREBOARD_RESPONSE_CACHE.clear()
    forecasts_route.forecasts_service._FORECASTS_SCOREBOARD_INFLIGHT.clear()

    snapshot = {
        "generated_at": FRESH_TS,
        "accuracy_metrics": {
            "hit_rate": 0.61,
            "mae": 0.07,
            "avg_confidence": 0.66,
            "total_predictions": 42,
        },
        "summary": {
            "total_predictions_analyzed": 42,
            "hit_rate_percentage": 61.0,
            "average_confidence": 0.66,
        },
        "by_horizon": {
            "1w": {
                "hit_rate": 0.58,
                "count": 18,
            }
        },
        "by_asset": {
            "AAPL": {
                "hit_rate": 0.63,
                "count": 9,
            }
        },
        "source": ["prediction_analyzer_service"],
    }

    monkeypatch.setattr(
        forecasts_route,
        "load_json",
        lambda key: snapshot if key in {"prediction_accuracy", "prediction_accuracy.json"} else {},
    )

    client = _client()
    path = "/forecasts/scoreboard?horizon=1w"

    first = client.get(path)
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first_data["cache"]["hit"] is False
    assert first_data["summary"]["hit_rate_percentage"] == 61.0
    assert first_data["threshold_summary"]["walk_forward_direction_hit_rate"]["target"] == 0.52
    assert any(row["scope"] == "overall" for row in first_data["rows"])
    assert any(row["scope"] == "horizon:1w" for row in first_data["rows"])
    assert first_data["rows"][0]["metric_key"] == "walk_forward_direction_hit_rate"
    assert first_data["updated_at"] == FRESH_TS
    assert first_data["provenance"]["source"] == first_data["source"]
    assert first_data["provenance"]["sla"]["updated_at"] == FRESH_TS

    second = client.get(path)
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["cache"]["hit"] is True
    assert "forecasts_scoreboard_cache_hit" in (second_data.get("source") or [])
    assert second_data["provenance"]["sla"]["updated_at"] == FRESH_TS


def test_walk_forward_scoreboard_debug_bypass_and_fallback(monkeypatch):
    forecasts_route.forecasts_service._FORECASTS_SCOREBOARD_RESPONSE_CACHE.clear()
    forecasts_route.forecasts_service._FORECASTS_SCOREBOARD_INFLIGHT.clear()

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: {})

    class _StubAnalyzer:
        def analyze_predictions(self, horizon: str = "all"):
            assert horizon == "all"
            return {
                "generated_at": FRESH_TS,
                "accuracy_metrics": {
                    "hit_rate": 0.0,
                    "mae": 0.0,
                    "avg_confidence": 0.0,
                    "total_predictions": 0,
                },
                "summary": {
                    "total_predictions_analyzed": 0,
                    "hit_rate_percentage": 0.0,
                    "average_confidence": 0.0,
                },
                "by_horizon": {},
                "by_asset": {},
                "source": ["prediction_analyzer_service", "empty_fallback"],
            }

    monkeypatch.setattr(forecasts_route.forecasts_service, "prediction_analyzer_service", _StubAnalyzer())

    client = _client()
    resp = client.get("/forecasts/scoreboard?debug=true")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["cache"]["hit"] is False
    assert isinstance(data.get("debug_pipeline"), list)
    assert data["count"] == 2
    assert data["summary"]["total_predictions_analyzed"] == 0
    assert data["updated_at"] == FRESH_TS
    assert data["provenance"]["fallback_used"] is False
