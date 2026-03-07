from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application import judge_endpoint_service


def test_judge_verdicts_payload_exposes_stable_metadata():
    now_iso = "2026-03-07T16:54:00Z"

    async def fake_compute_verdicts_fn(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "verdict": "buy",
                        "confidence": 0.61,
                    }
                ],
                "count": 1,
                "generated_at": now_iso,
            },
            "freshness": now_iso,
        }

    payload = asyncio.run(
        judge_endpoint_service.get_judge_verdicts_payload(
            limit=1,
            min_confidence=0.3,
            ticker=["AAPL"],
            sort_by="confidence",
            sort_order="desc",
            profile="balanced",
            debug=False,
            debug_full=False,
            x_debug_token=None,
            compute_verdicts_fn=fake_compute_verdicts_fn,
        )
    )

    assert payload["ok"] is True
    assert payload["freshness"] == now_iso
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["data"]["freshness"] == now_iso
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["error"] is None
    assert "metadata_contract_v1" in (payload["data"].get("source") or [])


def test_judge_options_fallback_exposes_degraded_metadata():
    def fail_risk_levels():
        raise RuntimeError("judge options exploded")

    payload = asyncio.run(
        judge_endpoint_service.get_judge_options_payload(
            risk_levels_fn=fail_risk_levels,
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert "judge options exploded" in str(payload["error"])
    assert payload["freshness"] == payload["data"]["freshness"]
    assert payload["data"]["status"] == "degraded"
    assert "judge options exploded" in str(payload["data"]["error"])
    assert payload["data"]["risk_levels"] == ["low", "medium", "high", "critical"]
