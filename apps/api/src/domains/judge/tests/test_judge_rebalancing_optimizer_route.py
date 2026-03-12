from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domains.judge.api import judge as judge_route  # noqa: E402
from services import judge_endpoint_service  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(judge_route.router)
    return TestClient(app)


def test_rebalancing_optimizer_lite_route_pins_profile(monkeypatch):
    captured = {}
    now_iso = "2026-03-12T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "SPY",
                        "horizon": "1m",
                        "expected_return": 0.0,
                        "risk_level": "medium",
                        "confidence": 0.64,
                        "summary": ["Trim equity overweight back toward target."],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": ["trim SPY", "add IEF"],
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
                    "avg_confidence": 0.64,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": 0.3,
                    "tickers": ["SPY"],
                    "sort_by": "confidence",
                    "sort_order": "desc",
                    "limit": 1,
                    "profile": "rebalancing_optimizer_lite",
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
    resp = client.get(
        "/api/judge/rebalancing-optimizer-lite?limit=1&ticker=SPY&portfolio_id=pf-rebal&debug=true"
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert captured["limit"] == 1
    assert captured["ticker"] == ["SPY"]
    assert captured["portfolio_id"] == "pf-rebal"
    assert captured["profile"] == "rebalancing_optimizer_lite"
    assert captured["debug"] is True
    assert callable(captured["compute_verdicts_fn"])
