from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application import judge_endpoint_service


def test_sector_company_transmission_builds_rows_and_degrades_confidence():
    async def fake_compute_verdicts_fn(**_kwargs):
        now_iso = "2026-03-11T05:00:00Z"
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "NVDA",
                        "sector": "Technology",
                        "horizon": "1w",
                        "expected_return": 0.03,
                        "confidence": 0.8,
                        "risk_level": "medium",
                        "summary": ["AI demand keeps semiconductor tone constructive."],
                        "impacts": {"equity": ["sector rotation", "chip demand resilience"]},
                    },
                    {
                        "ticker": "TSLA",
                        "horizon": "1w",
                        "expected_return": 0.01,
                        "confidence": 0.8,
                        "risk_level": "high",
                        "summary": ["Execution risk dominates despite positive tape."],
                        "impacts": {"equity": []},
                    },
                ],
                "generated_at": now_iso,
                "source": ["judge_route", "tests"],
            },
            "freshness": now_iso,
            "status": "ok",
            "error": None,
        }

    payload = asyncio.run(
        judge_endpoint_service.get_judge_sector_company_transmission_payload(
            limit=5,
            min_confidence=0.3,
            ticker=["NVDA", "TSLA"],
            portfolio_id=None,
            sort_by="confidence",
            sort_order="desc",
            profile="equity_1w",
            debug=False,
            debug_full=False,
            x_debug_token=None,
            compute_verdicts_fn=fake_compute_verdicts_fn,
        )
    )

    assert payload["ok"] is True
    rows = payload["data"]["rows"]
    assert len(rows) == 2
    assert rows[0]["sector"] == "Technology"
    assert rows[0]["transmission_factor"] > 0.0
    assert rows[0]["confidence_after_transmission"] < rows[0]["confidence_before_transmission"]
    assert rows[1]["sector"] == "unknown"
    assert rows[1]["transmission_uncertainty"] > rows[0]["transmission_uncertainty"]
    assert payload["data"]["stats"]["high_uncertainty_count"] == 1


def test_sector_company_transmission_returns_never_empty_fallback():
    async def fake_compute_verdicts_fn(**_kwargs):
        raise RuntimeError("judge unavailable")

    payload = asyncio.run(
        judge_endpoint_service.get_judge_sector_company_transmission_payload(
            limit=5,
            min_confidence=0.3,
            ticker=["NVDA"],
            portfolio_id=None,
            sort_by="confidence",
            sort_order="desc",
            profile="equity_1w",
            debug=False,
            debug_full=False,
            x_debug_token=None,
            compute_verdicts_fn=fake_compute_verdicts_fn,
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert payload["data"]["rows"] == []
    assert payload["data"]["count"] == 0
    assert payload["data"]["message"] == "Sector-to-company transmission unavailable; fallback returned."
