"""
Tests de non-régression pour la normalisation des verdicts judge.
"""
from __future__ import annotations

from src.services.judge_builder import build_judge_verdict


def _dump(verdict):
    if hasattr(verdict, "model_dump"):
        return verdict.model_dump(exclude_none=True)
    return verdict.dict(exclude_none=True)


def test_build_judge_verdict_hides_debug_fields_when_absent():
    row = {
        "ticker": "AAPL",
        "horizon": "1w",
        "expected_return": 0.01,
        "confidence": 0.72,
        "risk_level": "medium",
        "analysis": {
            "summary": ["Test summary"],
            "scenarios": [{"name": "base", "p": 60}],
            "risks": ["risk"],
            "impacts": {"equity": ["impact"]},
            "actions": ["action"],
            "confidence": 0.72,
            "phase_scores": {"technical": 0.65},
        },
        "generated_at": "2026-02-05T00:00:00Z",
        "source": ["judge_route", "forecasts_llm"],
    }

    verdict = build_judge_verdict(row, profile="equity_1w")
    payload = _dump(verdict)

    assert "debug_payload" not in payload
    assert "debug_llm_res" not in payload
    assert payload["ticker"] == "AAPL"
    assert payload["meta"]["profile"] == "equity_1w"


def test_build_judge_verdict_uses_provider_from_row_meta():
    row = {
        "ticker": "NVDA",
        "horizon": "1w",
        "expected_return": -0.02,
        "confidence": 0.61,
        "risk_level": "high",
        "analysis": {
            "summary": ["Summary"],
            "scenarios": [{"name": "base", "p": 70}, {"name": "bear", "p": 30}],
            "phase_scores": {"macro": 0.4},
        },
        "meta": {
            "provider": "openrouter",
            "generated_at": "2026-02-05T01:00:00Z",
        },
        "generated_at": "2026-02-05T01:00:00Z",
    }

    verdict = build_judge_verdict(row)
    assert verdict.meta.provider == "openrouter"
    assert abs(sum(sc.p for sc in verdict.scenarios) - 1.0) < 1e-9

