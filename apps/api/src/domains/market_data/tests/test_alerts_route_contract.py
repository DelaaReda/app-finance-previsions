from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.market_data.api import alerts as alerts_route  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(alerts_route.router)
    return TestClient(app)


def test_alerts_route_cache_hit_and_debug_bypass(monkeypatch):
    alerts_route._ALERTS_RESPONSE_CACHE.clear()

    snapshot = {
        "generated_at": "2026-03-13T05:45:00Z",
        "source": ["alerts_job"],
        "alerts": [
            {
                "id": "alert-urgent",
                "ticker": "NVDA",
                "priority_rank": 1,
                "priority_score": 410,
                "priority_band": "urgent",
                "severity": "high",
                "confidence": 0.91,
                "timestamp": "2026-03-13T05:45:00Z",
            }
        ],
        "suppressed_alerts": [],
        "stats": {
            "priority_bands": {"urgent": 1},
            "suppression_reasons": {},
        },
        "warnings": [],
    }

    monkeypatch.setattr(alerts_route, "get_latest_alerts", lambda: snapshot)
    client = _client()

    first = client.get("/api/alerts?limit=5")
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first_data["cache"]["hit"] is False
    assert first_data["count"] == 1
    assert first_data["queue"]["top_alert_id"] == "alert-urgent"

    second = client.get("/api/alerts?limit=5")
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["cache"]["hit"] is True
    assert "alerts_route_cache_hit" in (second_data.get("source") or [])

    debug_resp = client.get("/api/alerts?limit=5&debug=true")
    assert debug_resp.status_code == 200
    debug_data = debug_resp.json()["data"]
    assert debug_data["cache"]["hit"] is False
    assert "alerts_route_cache_hit" not in (debug_data.get("source") or [])
    assert isinstance(debug_data.get("debug_pipeline"), list)


def test_alerts_route_filters_priority_band_and_suppressed_preview(monkeypatch):
    alerts_route._ALERTS_RESPONSE_CACHE.clear()

    snapshot = {
        "generated_at": "2026-03-13T05:45:00Z",
        "source": ["alerts_job"],
        "alerts": [
            {
                "id": "alert-medium",
                "ticker": "AAPL",
                "priority_rank": 2,
                "priority_score": 280,
                "priority_band": "high",
                "severity": "medium",
                "confidence": 0.74,
                "timestamp": "2026-03-13T05:44:00Z",
            },
            {
                "id": "alert-low",
                "ticker": "MSFT",
                "priority_rank": 3,
                "priority_score": 180,
                "priority_band": "medium",
                "severity": "low",
                "confidence": 0.52,
                "timestamp": "2026-03-13T05:43:00Z",
            },
        ],
        "suppressed_alerts": [
            {
                "id": "suppressed-high",
                "ticker": "AAPL",
                "priority_rank": 4,
                "priority_score": 260,
                "priority_band": "high",
                "severity": "medium",
                "confidence": 0.71,
                "timestamp": "2026-03-13T05:40:00Z",
                "suppression": {"reason": "fatigue_window_duplicate"},
            }
        ],
        "stats": {
            "priority_bands": {"high": 1, "medium": 1},
            "suppression_reasons": {"fatigue_window_duplicate": 1},
        },
        "warnings": ["duplicate_alerts_suppressed"],
    }

    monkeypatch.setattr(alerts_route, "get_latest_alerts", lambda: snapshot)
    client = _client()

    resp = client.get("/api/alerts?priority_band=high&include_suppressed=true&limit=3")
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert [row["id"] for row in data["alerts"]] == ["alert-medium"]
    assert [row["id"] for row in data["suppressed_alerts"]] == ["suppressed-high"]
    assert data["filters_applied"] == {
        "priority_band": "high",
        "include_suppressed": True,
        "limit": 3,
    }
    assert data["stats"]["suppressed_available"] == 1
    assert data["stats"]["returned_suppressed_count"] == 1
    assert "duplicate_alerts_suppressed" in data["warnings"]


def test_alerts_route_fallback_keeps_contract(monkeypatch):
    alerts_route._ALERTS_RESPONSE_CACHE.clear()

    def _boom():
        raise RuntimeError("snapshot unavailable")

    monkeypatch.setattr(alerts_route, "get_latest_alerts", _boom)
    client = _client()

    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["count"] == 0
    assert data["alerts"] == []
    assert data["freshness"] == "error"
    assert "alerts_route_fallback" in (data.get("source") or [])
    assert data["cache"]["hit"] is False
    assert data["filters_applied"]["limit"] == 20
