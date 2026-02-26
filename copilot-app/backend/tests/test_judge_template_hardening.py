from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.services.judge_builder import build_judge_verdict

ROUTES_PATH = Path(__file__).resolve().parents[1] / "src" / "api" / "routes"
if str(ROUTES_PATH) not in sys.path:
    sys.path.insert(0, str(ROUTES_PATH))

import judge as judge_route  # type: ignore  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(judge_route.router)
    return TestClient(app)


def test_judge_query_validation_rejects_invalid_sort_order():
    client = _client()
    resp = client.get("/api/judge?sort_order=foo")
    assert resp.status_code == 422


def test_judge_openapi_exposes_enum_params_and_response_schema():
    client = _client()
    payload = client.get("/openapi.json").json()
    judge_get = payload["paths"]["/api/judge"]["get"]
    params = {p["name"]: p.get("schema", {}) for p in judge_get.get("parameters", [])}

    assert params["sort_order"].get("enum") == ["asc", "desc"]
    assert params["sort_by"].get("enum") == [
        "confidence",
        "expected_return",
        "score",
        "risk_level",
        "timestamp",
    ]

    response_schema = (
        judge_get["responses"]["200"]["content"]["application/json"]["schema"]
    )
    assert response_schema, "Judge 200 response schema must not be empty."


def test_judge_singleflight_executes_compute_once_for_same_cache_key():
    judge_route._JUDGE_INFLIGHT.clear()
    calls = {"count": 0}

    async def compute_once():
        calls["count"] += 1
        await asyncio.sleep(0.02)
        return {"value": "ok"}

    async def run_batch():
        return await asyncio.gather(
            judge_route._compute_singleflight("k1", compute_once),
            judge_route._compute_singleflight("k1", compute_once),
            judge_route._compute_singleflight("k1", compute_once),
        )

    results = asyncio.run(run_batch())
    leaders = [is_leader for _, is_leader in results]
    payloads = [payload for payload, _ in results]

    assert calls["count"] == 1
    assert leaders.count(True) == 1
    assert all(p == {"value": "ok"} for p in payloads)


def test_judge_builder_keeps_critical_risk_level():
    row = {
        "ticker": "TSLA",
        "horizon": "1w",
        "expected_return": -0.03,
        "confidence": 0.51,
        "risk_level": "CRITICAL",
        "analysis": {
            "summary": ["Risk elevated"],
            "scenarios": [{"name": "base", "p": 55}, {"name": "bear", "p": 45}],
            "risks": ["volatility"],
            "actions": ["hedge"],
        },
        "generated_at": "2026-02-26T00:00:00Z",
        "source": ["judge_route", "forecasts_llm"],
    }

    verdict = build_judge_verdict(row)
    assert verdict.risk_level == "critical"


def test_judge_debug_sanitizer_hides_raw_llm_fields():
    raw = {
        "ok": True,
        "provider": "codestral",
        "model": "codestral-2508",
        "usage": {"total_tokens": 111},
        "answer": "x" * 2000,
        "raw": {"content": "should_not_leak"},
    }
    sanitized = judge_route._sanitize_debug_llm_res(raw)

    assert "raw" not in sanitized
    assert sanitized["provider"] == "codestral"
    assert "answer_excerpt" in sanitized
    assert len(sanitized["answer_excerpt"]) <= (
        judge_route.JUDGE_DEBUG_ANSWER_SNIPPET_CHARS + 1
    )


def test_judge_public_sanitizer_hides_raw_and_debug_fields_when_not_requested():
    row = {
        "ticker": "AAPL",
        "raw_answer": "secret",
        "debug_payload": {"foo": 1},
        "debug_llm_res": {"raw": "sensitive"},
    }
    sanitized = judge_route._sanitize_verdict_for_public(
        row,
        keep_raw=False,
        keep_debug_fields=False,
    )
    assert "raw_answer" not in sanitized
    assert "debug_payload" not in sanitized
    assert "debug_llm_res" not in sanitized


def test_judge_response_model_excludes_none_debug_fields(monkeypatch):
    judge_route._JUDGE_RESPONSE_CACHE.clear()

    async def _fake_singleflight(_cache_key, _compute_fn):
        return (
            {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "horizon": "1w",
                        "expected_return": 0.01,
                        "risk_level": "medium",
                        "confidence": 0.61,
                        "summary": ["Synthetic verdict for contract test"],
                        "meta": {
                            "generated_at": "2026-02-26T00:00:00Z",
                            "source": ["judge_route", "tests"],
                        },
                    }
                ],
                "count": 1,
                "stats": {
                    "total_verdicts": 1,
                    "high_confidence_count": 0,
                    "avg_confidence": 0.61,
                    "generated_at": "2026-02-26T00:00:00Z",
                },
                "filters_applied": {
                    "min_confidence": 0.3,
                    "tickers": ["AAPL"],
                    "sort_by": "confidence",
                    "sort_order": "desc",
                    "limit": 1,
                },
                "generated_at": "2026-02-26T00:00:00Z",
                "source": ["judge_route", "tests"],
            },
            True,
        )

    monkeypatch.setattr(judge_route, "_compute_singleflight", _fake_singleflight)
    client = _client()
    resp = client.get("/api/judge?limit=1&ticker=AAPL&debug=false")
    assert resp.status_code == 200
    payload = resp.json()
    data = payload["data"]
    verdict = data["verdicts"][0]

    assert "debug_pipeline" not in data
    assert "verdicts_raw" not in data
    assert "raw_answer" not in verdict
    assert "debug_payload" not in verdict
    assert "debug_llm_res" not in verdict
