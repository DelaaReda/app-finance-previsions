from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROUTES_PATH = Path(__file__).resolve().parents[1] / "src" / "api" / "routes"
SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(ROUTES_PATH) not in sys.path:
    sys.path.insert(0, str(ROUTES_PATH))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import judge as judge_route  # type: ignore  # noqa: E402
from services import judge_endpoint_service  # type: ignore  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(judge_route.router)
    return TestClient(app)


def test_judge_route_delegates_to_service(monkeypatch):
    captured = {}

    async def fake_get_judge_verdicts_payload(**kwargs):
        captured.update(kwargs)
        now_iso = "2026-02-28T00:00:00Z"
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "horizon": "1w",
                        "expected_return": 0.01,
                        "risk_level": "medium",
                        "confidence": 0.61,
                        "summary": ["Synthetic verdict"],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": [],
                        "phase_scores": {},
                        "data_needed": [],
                        "attachments": [],
                        "meta": {
                            "generated_at": now_iso,
                            "source": ["judge_route", "tests"],
                        },
                    }
                ],
                "count": 1,
                "stats": {
                    "total_verdicts": 1,
                    "high_confidence_count": 0,
                    "avg_confidence": 0.61,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": 0.3,
                    "tickers": ["AAPL"],
                    "sort_by": "confidence",
                    "sort_order": "desc",
                    "limit": 1,
                },
                "generated_at": now_iso,
                "source": ["judge_route", "tests"],
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_verdicts_payload",
        fake_get_judge_verdicts_payload,
    )

    client = _client()
    resp = client.get("/api/judge?limit=1&ticker=AAPL&debug=true")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert captured["limit"] == 1
    assert captured["ticker"] == ["AAPL"]
    assert captured["debug"] is True
    assert callable(captured["compute_verdicts_fn"])


def test_judge_quality_route_delegates_to_service(monkeypatch):
    async def fake_quality(**kwargs):
        return {
            "ok": True,
            "data": {"as_of": "2026-02-28T00:00:00Z", "horizon_days": kwargs["horizon_days"], "min_samples": kwargs["min_samples"]},
            "freshness": "2026-02-28T00:00:00Z",
        }

    monkeypatch.setattr(judge_endpoint_service, "get_judge_quality_payload", fake_quality)
    client = _client()
    resp = client.get("/api/judge/quality?horizon_days=7&min_samples=25")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["horizon_days"] == 7
    assert payload["data"]["min_samples"] == 25


def test_judge_options_route_delegates_to_service(monkeypatch):
    async def fake_options(**_kwargs):
        return {
            "ok": True,
            "data": {
                "sort_options": [{"value": "confidence", "label": "Confiance"}],
                "risk_levels": ["low", "medium", "high", "critical"],
                "confidence_thresholds": [{"label": "Toutes", "value": 0.0}],
                "generated_at": "2026-02-28T00:00:00Z",
            },
            "freshness": "2026-02-28T00:00:00Z",
        }

    monkeypatch.setattr(judge_endpoint_service, "get_judge_options_payload", fake_options)
    client = _client()
    resp = client.get("/api/judge/options")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["risk_levels"] == ["low", "medium", "high", "critical"]
