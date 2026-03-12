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


def test_rebalancing_strategy_playbooks_keep_degraded_empty_contract(monkeypatch):
    now_iso = "2026-03-12T12:10:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [],
                "count": 0,
                "stats": {"total_verdicts": 0},
                "generated_at": now_iso,
                "source": ["judge_route", "tests"],
                "warnings": ["portfolio_context_unavailable"],
                "status": "degraded",
                "error": "portfolio context unavailable",
            },
            "freshness": now_iso,
            "status": "degraded",
            "error": "portfolio context unavailable",
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_verdicts_payload",
        fake_get_judge_verdicts_payload,
    )

    client = _client()
    resp = client.get(
        "/api/judge/strategy-playbooks?limit=1&portfolio_id=pf-rebal&profile=rebalancing_optimizer_lite"
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert payload["error"] == "portfolio context unavailable"
    assert payload["data"]["playbooks"] == []
    assert payload["data"]["count"] == 0
    assert payload["data"]["warnings"] == ["portfolio_context_unavailable"]
    assert payload["data"]["filters_applied"] == {
        "min_confidence": 0.3,
        "tickers": [],
        "sort_by": "confidence",
        "sort_order": "desc",
        "limit": 1,
        "profile": "rebalancing_optimizer_lite",
    }
    assert payload["data"]["stats"] == {
        "go_count": 0,
        "no_go_count": 0,
        "avg_confidence": 0.0,
    }
    assert "judge_strategy_playbook_route" in payload["data"]["source"]
    assert "judge_route" in payload["data"]["source"]


def test_rebalancing_strategy_playbooks_surface_turnover_and_risk_delta(monkeypatch):
    now_iso = "2026-03-12T12:20:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "IEF",
                        "horizon": "1m",
                        "expected_return": 0.018,
                        "risk_level": "low",
                        "confidence": 0.74,
                        "summary": ["Rotate toward duration to reduce portfolio risk."],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": ["trim SPY", "add IEF"],
                        "phase_scores": {},
                        "data_needed": [],
                        "attachments": [],
                        "go_no_go": {
                            "decision": "hold",
                            "reasons": ["Reduce drawdown concentration"],
                        },
                        "debug_payload": {
                            "features": {
                                "portfolio_context": {
                                    "risk_level": "high",
                                    "weights": {"SPY": 0.60, "IEF": 0.40},
                                }
                            }
                        },
                        "meta": {
                            "generated_at": now_iso,
                            "source": ["judge_route", "tests"],
                        },
                    }
                ],
                "count": 1,
                "stats": {"total_verdicts": 1},
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
        "/api/judge/strategy-playbooks?limit=1&portfolio_id=pf-rebal&profile=rebalancing_optimizer_lite"
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert payload["data"]["playbooks"][0]["turnover"] == 10.0
    assert payload["data"]["playbooks"][0]["risk_delta"] == -2
    assert payload["data"]["playbooks"][0]["profile"] == "rebalancing_optimizer_lite"
