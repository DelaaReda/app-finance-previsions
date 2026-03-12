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
