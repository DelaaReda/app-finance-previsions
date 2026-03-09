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


def test_judge_route_preserves_canonical_status_metadata(monkeypatch):
    now_iso = "2026-03-08T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
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
                "freshness": now_iso,
                "status": "degraded",
                "warnings": ["partial_data_provider_timeout"],
                "error": "provider timeout",
                "source": ["judge_route", "tests"],
            },
            "freshness": now_iso,
            "status": "degraded",
            "error": "provider timeout",
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_verdicts_payload",
        fake_get_judge_verdicts_payload,
    )

    client = _client()
    resp = client.get("/api/judge?limit=1&ticker=AAPL")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "degraded"
    assert payload["error"] == "provider timeout"
    assert payload["data"]["status"] == "degraded"
    assert payload["data"]["freshness"] == now_iso
    assert payload["data"]["warnings"] == ["partial_data_provider_timeout"]


def test_judge_route_keeps_decision_journal_contract_fields(monkeypatch):
    now_iso = "2026-03-08T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "decision_id": "judge_demo_aapl",
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
                "decision_journal": {
                    "schema_version": "decision_journal_v1",
                    "generated_at": now_iso,
                    "count": 1,
                    "append_only": True,
                    "link_field": "decision_id",
                    "outcomes_update_mode": "separate_records",
                    "feedback_horizons": ["1d", "1w", "1m"],
                    "entries": [
                        {
                            "decision_id": "judge_demo_aapl",
                            "date": "2026-03-08",
                            "captured_at": now_iso,
                            "ticker": "AAPL",
                            "action": "buy",
                            "confidence": 0.61,
                            "horizon": "1w",
                            "why": ["Synthetic verdict"],
                            "risk": {"level": "medium", "caveat": ""},
                            "sources": ["judge_route", "tests"],
                            "profile": "balanced",
                        }
                    ],
                },
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_verdicts_payload",
        fake_get_judge_verdicts_payload,
    )

    client = _client()
    resp = client.get("/api/judge?limit=1&ticker=AAPL")
    assert resp.status_code == 200
    payload = resp.json()
    verdict = payload["data"]["verdicts"][0]
    journal = payload["data"]["decision_journal"]

    assert verdict["decision_id"] == "judge_demo_aapl"
    assert journal["schema_version"] == "decision_journal_v1"
    assert journal["link_field"] == "decision_id"
    assert journal["entries"][0]["decision_id"] == verdict["decision_id"]


def test_judge_route_preserves_decision_feedback_loop_payload(monkeypatch):
    now_iso = "2026-03-08T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "decision_id": "judge_demo_aapl",
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
                "decision_journal": {
                    "schema_version": "decision_journal_v1",
                    "generated_at": now_iso,
                    "count": 1,
                    "append_only": True,
                    "link_field": "decision_id",
                    "outcomes_update_mode": "separate_records",
                    "feedback_horizons": ["1d", "1w", "1m"],
                    "feedback_loop": {
                        "schema_version": "decision_outcome_feedback_v1",
                        "update_mode": "separate_records",
                        "tracked_horizons": ["1d", "1w", "1m"],
                        "pending_entries": 1,
                        "pending_feedback_records": 3,
                    },
                    "store": {
                        "status": "persisted",
                        "storage_key": "decision_journal",
                        "schema_version": "decision_journal_v1",
                        "persisted_count": 1,
                        "total_entries": 1,
                        "path": "runtime/data/decision_journal.json",
                    },
                    "entries": [
                        {
                            "decision_id": "judge_demo_aapl",
                            "date": "2026-03-08",
                            "captured_at": now_iso,
                            "ticker": "AAPL",
                            "action": "buy",
                            "confidence": 0.61,
                            "horizon": "1w",
                            "why": ["Synthetic verdict"],
                            "risk": {"level": "medium", "caveat": ""},
                            "prediction": {
                                "expected_return": 0.01,
                                "score": 0.71,
                            },
                            "outcome_feedback": {
                                "schema_version": "decision_outcome_feedback_v1",
                                "status": "pending",
                                "update_mode": "separate_records",
                                "latest_feedback_at": None,
                                "next_checkpoint": {
                                    "horizon": "1d",
                                    "status": "pending",
                                    "due_at": "2026-03-09T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                                "checkpoints": [
                                    {
                                        "horizon": "1d",
                                        "status": "pending",
                                        "due_at": "2026-03-09T00:00:00Z",
                                        "record_mode": "separate_record",
                                    }
                                ],
                            },
                            "sources": ["judge_route", "tests"],
                            "profile": "balanced",
                        }
                    ],
                },
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_verdicts_payload",
        fake_get_judge_verdicts_payload,
    )

    client = _client()
    resp = client.get("/api/judge?limit=1&ticker=AAPL")
    assert resp.status_code == 200
    payload = resp.json()
    journal = payload["data"]["decision_journal"]
    entry = journal["entries"][0]

    assert journal["feedback_loop"]["pending_feedback_records"] == 3
    assert journal["store"]["storage_key"] == "decision_journal"
    assert entry["prediction"] == {"expected_return": 0.01, "score": 0.71}
    assert entry["outcome_feedback"]["status"] == "pending"
    assert entry["outcome_feedback"]["next_checkpoint"]["horizon"] == "1d"


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


def test_judge_decision_journal_route_delegates_to_service(monkeypatch):
    captured = {}

    async def fake_decision_journal_payload(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "schema_version": "decision_journal_v1",
                "record_mode": "append_only",
                "filters": {
                    "decision_id": "judge_demo_aapl",
                    "profile": None,
                    "status": "in_progress",
                },
                "count": 1,
                "filtered_count": 1,
                "returned_count": 1,
                "entries": [
                    {
                        "decision_id": "judge_demo_aapl",
                        "captured_at": "2026-03-08T00:00:00Z",
                        "ticker": "AAPL",
                    }
                ],
            },
            "freshness": "2026-03-08T00:00:00Z",
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_decision_journal_payload",
        fake_decision_journal_payload,
    )
    client = _client()
    resp = client.get(
        "/api/judge/decision-journal?decision_id=judge_demo_aapl&status=in_progress&limit=10"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert captured["decision_id"] == "judge_demo_aapl"
    assert captured["status_filter"] == "in_progress"
