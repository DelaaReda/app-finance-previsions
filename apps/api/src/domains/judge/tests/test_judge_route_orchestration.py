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
    resp = client.get("/api/judge?limit=1&ticker=AAPL&portfolio_id=pf-123&debug=true")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert captured["limit"] == 1
    assert captured["ticker"] == ["AAPL"]
    assert captured["portfolio_id"] == "pf-123"
    assert captured["debug"] is True
    assert callable(captured["compute_verdicts_fn"])


def test_judge_strategy_playbooks_maps_verdicts(monkeypatch):
    captured = {}
    now_iso = "2026-02-28T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "horizon": "1w",
                        "expected_return": 0.018,
                        "risk_level": "high",
                        "confidence": 0.71,
                        "summary": ["Bullish setup", "Momentum positive"],
                        "scenarios": [
                            {
                                "name": "risk_off",
                                "p": 0.28,
                                "description": "Market reprices risk",
                            },
                        ],
                        "risks": ["inflation", "macro shock"],
                        "impacts": {"equity": ["sector rotation"], "rates": []},
                        "actions": ["reduce position", "hedge"],
                        "phase_scores": {},
                        "data_needed": [],
                        "attachments": [],
                        "go_no_go": {
                            "decision": "go",
                            "reasons": ["high confidence", "strong momentum"],
                        },
                        "meta": {
                            "generated_at": now_iso,
                            "source": ["judge_route", "tests"],
                        },
                    }
                ],
                "count": 1,
                "stats": {
                    "total_verdicts": 1,
                    "high_confidence_count": 1,
                    "avg_confidence": 0.71,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": 0.3,
                    "tickers": ["AAPL"],
                    "sort_by": "confidence",
                    "sort_order": "desc",
                    "limit": 1,
                    "profile": "equity_1w",
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
        "/api/judge/strategy-playbooks?limit=1&ticker=AAPL&portfolio_id=pf-123&profile=equity_1w"
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert payload["data"]["playbooks"][0]["playbook_id"] == "AAPL:1w:go:equity_1w"
    assert payload["data"]["playbooks"][0]["decision"] == "go"
    assert payload["data"]["playbooks"][0]["risk_level"] == "high"
    assert payload["data"]["playbooks"][0]["conflicts"] == ["risk_profile_too_aggressive"]
    assert payload["data"]["stats"]["go_count"] == 1

    assert captured["limit"] == 1
    assert captured["ticker"] == ["AAPL"]
    assert captured["portfolio_id"] == "pf-123"
    assert captured["profile"] == "equity_1w"
    assert callable(captured["compute_verdicts_fn"])


def test_judge_strategy_playbooks_marks_signal_divergence(monkeypatch):
    now_iso = "2026-02-28T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "MSFT",
                        "horizon": "1w",
                        "expected_return": 0.01,
                        "risk_level": "low",
                        "confidence": 0.72,
                        "summary": ["Positive setup but risk gate override."],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": ["trim position"],
                        "phase_scores": {},
                        "data_needed": [],
                        "attachments": [],
                        "go_no_go": {
                            "decision": "no_go",
                            "reasons": ["hard risk gate"],
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
    resp = client.get("/api/judge/strategy-playbooks?limit=1&ticker=MSFT")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["data"]["playbooks"][0]["ticker"] == "MSFT"
    assert payload["data"]["playbooks"][0]["decision"] == "no_go"
    assert payload["data"]["playbooks"][0]["conflicts"] == ["signal_divergence"]


def test_judge_sector_company_transmission_route_delegates_to_service(monkeypatch):
    captured = {}
    now_iso = "2026-03-11T05:00:00Z"

    async def fake_get_judge_sector_company_transmission_payload(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "rows": [
                    {
                        "ticker": "NVDA",
                        "sector": "Technology",
                        "transmission_factor": 0.72,
                        "transmission_confidence": 0.69,
                        "transmission_uncertainty": 0.31,
                        "confidence_before_transmission": 0.8,
                        "confidence_after_transmission": 0.71,
                    }
                ],
                "count": 1,
                "generated_at": now_iso,
                "source": ["judge_route", "tests"],
            },
            "freshness": now_iso,
            "status": "ok",
            "error": None,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_sector_company_transmission_payload",
        fake_get_judge_sector_company_transmission_payload,
    )

    client = _client()
    resp = client.get(
        "/api/judge/sector-company-transmission?limit=1&ticker=NVDA&portfolio_id=pf-123&debug=true"
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert captured["limit"] == 1
    assert captured["ticker"] == ["NVDA"]
    assert captured["portfolio_id"] == "pf-123"
    assert captured["debug"] is True
    assert callable(captured["compute_verdicts_fn"])


def test_judge_strategy_playbooks_supports_items_legacy_payload(monkeypatch):
    now_iso = "2026-02-28T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "items": [
                    {
                        "ticker": "GOOG",
                        "horizon": "1m",
                        "expected_return": 0.0,
                        "risk_level": "medium",
                        "confidence": 0.55,
                        "summary": "Hold; mixed macro and macro setup.",
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": ["hold", "monitor"],
                        "phase_scores": {},
                        "data_needed": ["earnings"],
                        "go_no_go": {"decision": "hold"},
                        "meta": {"generated_at": now_iso, "source": ["judge_route", "tests"]},
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
    resp = client.get("/api/judge/strategy-playbooks?limit=1")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert payload["data"]["playbooks"][0]["playbook_id"] == "GOOG:1m:hold:equity_1w"


def test_judge_strategy_playbooks_merges_upstream_conflicts(monkeypatch):
    now_iso = "2026-02-28T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "TSLA",
                        "horizon": "1w",
                        "expected_return": 0.045,
                        "risk_level": "low",
                        "confidence": 0.72,
                        "summary": ["Mixed macro support"],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": ["trim"],
                        "phase_scores": {},
                        "data_needed": [],
                        "go_no_go": {
                            "decision": "no_go",
                            "reasons": ["manual override"],
                        },
                        "conflicts": ["manual_override", "Manual_Override"],
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
                    "avg_confidence": 0.48,
                    "generated_at": now_iso,
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
    resp = client.get("/api/judge/strategy-playbooks?limit=1&ticker=TSLA")
    assert resp.status_code == 200
    payload = resp.json()

    conflicts = payload["data"]["playbooks"][0]["conflicts"]
    assert conflicts == [
        "manual_override",
        "positive_signal_overridden_by_filters",
        "signal_divergence",
    ]


def test_judge_strategy_playbooks_preserves_upstream_contract_fields(monkeypatch):
    now_iso = "2026-02-28T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "horizon": "1w",
                        "expected_return": 0.02,
                        "risk_level": "medium",
                        "confidence": 0.9,
                        "summary": ["Synthetic verdict"],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": [],
                        "phase_scores": {},
                        "data_needed": [],
                        "attachments": [],
                        "go_no_go": {
                            "decision": "go",
                            "reasons": ["freshness_gate"],
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
                "cache": {
                    "hit": True,
                    "age_seconds": 12.34,
                    "ttl_seconds": 120,
                },
                "warnings": ["partial_data_provider_timeout"],
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
    resp = client.get("/api/judge/strategy-playbooks?limit=1&ticker=AAPL")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert payload["error"] == "provider timeout"
    assert payload["data"]["cache"]["hit"] is True
    assert payload["data"]["warnings"] == ["partial_data_provider_timeout"]
    assert "judge_strategy_playbook_route" in payload["data"]["source"]
    assert "judge_route" in payload["data"]["source"]
    assert payload["data"]["playbooks"]


def test_judge_strategy_playbooks_debug_exposes_debug_artifacts(monkeypatch):
    now_iso = "2026-02-28T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "horizon": "1w",
                        "expected_return": 0.02,
                        "risk_level": "medium",
                        "confidence": 0.82,
                        "summary": ["Synthetic verdict"],
                        "scenarios": [],
                        "risks": [],
                        "impacts": {},
                        "actions": [],
                        "phase_scores": {},
                        "data_needed": [],
                        "attachments": [],
                        "go_no_go": {
                            "decision": "go",
                            "reasons": ["freshness_gate"],
                        },
                        "debug_payload": {"question_excerpt": "sanitized payload"},
                        "debug_llm_res": {"provider": "gpt-test"},
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
                "debug_pipeline": [{"event": "compute", "stage": "row_done"}],
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_verdicts_payload",
        fake_get_judge_verdicts_payload,
    )

    client = _client()
    resp = client.get("/api/judge/strategy-playbooks?limit=1&ticker=AAPL&debug=true")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["ok"] is True
    assert payload["data"]["debug_payload"] == [{"question_excerpt": "sanitized payload"}]
    assert payload["data"]["debug_llm_res"] == [{"provider": "gpt-test"}]
    assert payload["data"]["debug_pipeline"] == [{"event": "compute", "stage": "row_done"}]


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


def test_judge_route_keeps_explainability_graph_contract(monkeypatch):
    now_iso = "2026-03-08T00:00:00Z"

    async def fake_get_judge_verdicts_payload(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "NVDA",
                        "decision_id": "judge_demo_nvda",
                        "horizon": "1w",
                        "expected_return": 0.03,
                        "risk_level": "medium",
                        "confidence": 0.82,
                        "summary": ["Demand remains strong."],
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
                "generated_at": now_iso,
                "source": ["judge_route", "tests", "judge_explainability_graph_v1"],
                "explainability": {
                    "schema_version": "judge_explainability_graph_v1",
                    "generated_at": now_iso,
                    "graph": {
                        "nodes": [
                            {
                                "id": "verdict:judge_demo_nvda",
                                "label": "NVDA",
                                "kind": "verdict",
                                "ticker": "NVDA",
                                "weight": 0.82,
                            },
                            {
                                "id": "source:news:reuters",
                                "label": "NVIDIA demand accelerates",
                                "kind": "news_item",
                                "weight": 0.91,
                                "quality_score": 0.88,
                                "freshness": {
                                    "timestamp": "2026-03-07T20:00:00Z",
                                    "age_hours": 4.0,
                                },
                            },
                        ],
                        "edges": [
                            {
                                "from": "source:news:reuters",
                                "to": "verdict:judge_demo_nvda",
                                "relationship": "supports",
                                "weight": 0.91,
                                "trace": {
                                    "origin": "debug_payload.news",
                                    "publisher": "Reuters",
                                },
                            }
                        ],
                    },
                    "source_traceability": [
                        {
                            "verdict_id": "verdict:judge_demo_nvda",
                            "ticker": "NVDA",
                            "primary_source_count": 1,
                            "supporting_sources": [
                                {
                                    "source_id": "news:reuters",
                                    "label": "NVIDIA demand accelerates",
                                    "kind": "news_item",
                                    "weight": 0.91,
                                    "quality_score": 0.88,
                                    "freshness": {
                                        "timestamp": "2026-03-07T20:00:00Z",
                                        "age_hours": 4.0,
                                    },
                                }
                            ],
                        }
                    ],
                    "stats": {
                        "verdict_count": 1,
                        "source_count": 1,
                        "edge_count": 1,
                        "stale_source_count": 0,
                        "broken_source_count": 0,
                        "avg_source_weight": 0.91,
                    },
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
    resp = client.get("/api/judge?limit=1&ticker=NVDA")
    assert resp.status_code == 200
    payload = resp.json()
    explainability = payload["data"]["explainability"]

    assert "judge_explainability_graph_v1" in (payload["data"].get("source") or [])
    assert explainability["schema_version"] == "judge_explainability_graph_v1"
    assert explainability["graph"]["nodes"][0]["ticker"] == "NVDA"
    assert explainability["graph"]["edges"][0]["relationship"] == "supports"
    assert explainability["source_traceability"][0]["primary_source_count"] == 1
    assert explainability["source_traceability"][0]["supporting_sources"][0]["freshness"]["age_hours"] == 4.0
    assert explainability["stats"]["avg_source_weight"] == 0.91


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


def test_judge_geopolitical_risk_graph_route_delegates_to_service(monkeypatch):
    captured = {}
    now_iso = "2026-03-10T00:00:00Z"

    async def fake_geopolitical_graph(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "generated_at": now_iso,
                "freshness": now_iso,
                "source": ["judge_geopolitical_risk_graph_service", "tests"],
                "filters_applied": {"region": "ukraine", "limit": 2},
                "stats": {
                    "article_count": 3,
                    "regions_detected": 1,
                    "edges_returned": 1,
                    "alerts_count": 1,
                },
                "nodes": [
                    {
                        "id": "ukraine",
                        "label": "ukraine",
                        "kind": "region",
                        "article_count": 3,
                        "recent_count": 2,
                        "event_count": 2,
                        "escalation_score": 0.8,
                        "escalation_band": "high",
                        "latest_at": now_iso,
                        "sample_headlines": ["Synthetic conflict update"],
                    }
                ],
                "edges": [
                    {
                        "source": "ukraine",
                        "target": "sanctions",
                        "kind": "region_to_event",
                        "weight": 2,
                        "recent_weight": 1,
                    }
                ],
                "alerts": [
                    {
                        "region": "ukraine",
                        "escalation_band": "high",
                        "escalation_score": 0.8,
                        "timestamp": now_iso,
                    }
                ],
                "warnings": [],
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_geopolitical_risk_graph_payload",
        fake_geopolitical_graph,
    )
    client = _client()
    resp = client.get("/api/judge/geopolitical-risk-graph?region=ukraine&limit=2")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["stats"]["alerts_count"] == 1
    assert payload["data"]["nodes"][0]["id"] == "ukraine"
    assert captured == {"region": "ukraine", "limit": 2}


def test_judge_event_impact_horizon_matrix_route_delegates_to_service(monkeypatch):
    captured = {}
    now_iso = "2026-03-10T00:00:00Z"

    async def fake_event_impact_horizon_matrix(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "generated_at": now_iso,
                "freshness": now_iso,
                "source": ["judge_event_impact_horizon_matrix_service", "tests"],
                "filters_applied": {"event_type": "sanctions", "limit": 2},
                "stats": {
                    "article_count": 3,
                    "event_types_returned": 1,
                    "horizons": ["1d", "1w", "1m"],
                },
                "matrix": [
                    {
                        "event_type": "sanctions",
                        "article_count": 3,
                        "recent_count": 2,
                        "sentiment_bias": -0.2,
                        "cross_horizon_divergence": 0.18,
                        "horizons": {
                            "1d": {"impact_score": 0.6, "impact_band": "medium", "bias": "risk_off", "template": "Immediate repricing."},
                            "1w": {"impact_score": 0.78, "impact_band": "medium", "bias": "persistent", "template": "Weekly persistence."},
                            "1m": {"impact_score": 0.81, "impact_band": "high", "bias": "persistent", "template": "Monthly persistence."},
                        },
                        "sample_headlines": ["Synthetic sanctions update"],
                    }
                ],
                "templates": {
                    "cross_horizon_divergence": "Cross-horizon divergence is highest when the event creates immediate repricing but slower fundamental confirmation.",
                },
                "warnings": [],
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "get_judge_event_impact_horizon_matrix_payload",
        fake_event_impact_horizon_matrix,
    )
    client = _client()
    resp = client.get("/api/judge/event-impact-horizon-matrix?event_type=sanctions&limit=2")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["matrix"][0]["event_type"] == "sanctions"
    assert captured == {"event_type": "sanctions", "limit": 2}
