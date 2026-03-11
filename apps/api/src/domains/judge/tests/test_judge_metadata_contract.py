from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application import judge_endpoint_service


def test_judge_verdicts_payload_exposes_stable_metadata(monkeypatch):
    now_iso = "2026-03-07T16:54:00Z"
    saved_calls = []

    async def fake_compute_verdicts_fn(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "verdict": "buy",
                        "confidence": 0.61,
                        "expected_return": 0.08,
                        "score": 0.73,
                    }
                ],
                "count": 1,
                "generated_at": now_iso,
            },
            "freshness": now_iso,
        }

    def fake_load_json(_key):
        return {
            "schema_version": "decision_journal_v1",
            "entries": [],
        }

    def fake_save_json(key, payload, source=None, version="v1"):
        saved_calls.append(
            {
                "key": key,
                "payload": payload,
                "source": source,
                "version": version,
            }
        )
        return Path("runtime/data") / f"{key}.json"

    monkeypatch.setattr(judge_endpoint_service, "load_json", fake_load_json)
    monkeypatch.setattr(judge_endpoint_service, "save_json", fake_save_json)
    monkeypatch.setattr(
        judge_endpoint_service,
        "_decision_journal_dir",
        lambda: Path("runtime/data/decision_journal"),
    )
    monkeypatch.setattr(
        judge_endpoint_service,
        "_persist_immutable_decision_journal_entries",
        lambda entries, generated_at: {
            "status": "persisted",
            "storage_key_prefix": "decision_journal/entries",
            "schema_version": "decision_journal_v1",
            "path_prefix": "runtime/data/decision_journal/entries",
            "persisted_count": len(entries),
            "existing_count": 0,
            "failed_count": 0,
        },
    )

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
    assert payload["data"]["decision_journal"]["schema_version"] == "decision_journal_v1"
    assert payload["data"]["decision_journal"]["append_only"] is True
    assert payload["data"]["decision_journal"]["outcomes_update_mode"] == "separate_records"
    assert payload["data"]["decision_journal"]["feedback_horizons"] == ["1d", "1w", "1m"]
    assert payload["data"]["decision_journal"]["feedback_loop"] == {
        "schema_version": "decision_outcome_feedback_v1",
        "update_mode": "separate_records",
        "tracked_horizons": ["1d", "1w", "1m"],
        "pending_entries": 1,
        "pending_feedback_records": 3,
    }
    assert payload["data"]["decision_journal"]["store"] == {
        "status": "persisted",
        "storage_key": "decision_journal",
        "schema_version": "decision_journal_v1",
        "persisted_count": 1,
        "total_entries": 1,
        "path": "runtime/data/decision_journal.json",
        "immutable_store": {
            "status": "persisted",
            "storage_key_prefix": "decision_journal/entries",
            "schema_version": "decision_journal_v1",
            "path_prefix": "runtime/data/decision_journal/entries",
            "persisted_count": 1,
            "existing_count": 0,
            "failed_count": 0,
        },
    }
    assert payload["data"]["decision_journal"]["count"] == 1
    entry = payload["data"]["decision_journal"]["entries"][0]
    assert entry["ticker"] == "AAPL"
    assert entry["action"] == "buy"
    assert entry["confidence"] == 0.61
    assert entry["horizon"] == "1w"
    assert entry["decision_id"].startswith("judge_")
    assert entry["prediction"] == {"expected_return": 0.08, "score": 0.73}
    assert entry["outcome_feedback"]["schema_version"] == "decision_outcome_feedback_v1"
    assert entry["outcome_feedback"]["status"] == "pending"
    assert entry["outcome_feedback"]["update_mode"] == "separate_records"
    assert entry["outcome_feedback"]["latest_feedback_at"] is None
    assert entry["outcome_feedback"]["next_checkpoint"] == {
        "horizon": "1d",
        "status": "pending",
        "due_at": "2026-03-08T16:54:00Z",
        "record_mode": "separate_record",
    }
    assert entry["outcome_feedback"]["checkpoints"] == [
        {
            "horizon": "1d",
            "status": "pending",
            "due_at": "2026-03-08T16:54:00Z",
            "record_mode": "separate_record",
        },
        {
            "horizon": "1w",
            "status": "pending",
            "due_at": "2026-03-14T16:54:00Z",
            "record_mode": "separate_record",
        },
        {
            "horizon": "1m",
            "status": "pending",
            "due_at": "2026-04-06T16:54:00Z",
            "record_mode": "separate_record",
        },
    ]
    assert payload["data"]["verdicts"][0]["decision_id"] == entry["decision_id"]
    assert "metadata_contract_v1" in (payload["data"].get("source") or [])
    assert "decision_journal_projection_v1" in (payload["data"].get("source") or [])
    assert "decision_outcome_feedback_v1" in (payload["data"].get("source") or [])
    assert "decision_journal_store_v1" in (payload["data"].get("source") or [])
    assert "judge_explainability_graph_v1" in (payload["data"].get("source") or [])
    explainability = payload["data"]["explainability"]
    assert explainability["schema_version"] == "judge_explainability_graph_v1"
    assert explainability["stats"]["verdict_count"] == 1
    assert explainability["stats"]["source_count"] >= 1
    assert explainability["stats"]["edge_count"] >= 1
    assert explainability["source_traceability"][0]["ticker"] == "AAPL"
    assert explainability["source_traceability"][0]["primary_source_count"] >= 1
    saved_by_key = {call["key"]: call for call in saved_calls}
    assert set(saved_by_key) == {"decision_journal"}
    manifest_save = saved_by_key["decision_journal"]
    assert manifest_save["source"] == ["judge_endpoint_service", "decision_journal_store_v1"]
    assert manifest_save["version"] == "decision_journal_v1"
    assert manifest_save["payload"]["append_only"] is True
    assert manifest_save["payload"]["outcomes_update_mode"] == "separate_records"
    assert manifest_save["payload"]["entries"][0]["decision_id"] == entry["decision_id"]


def test_judge_verdicts_payload_builds_weighted_source_traceability(monkeypatch):
    now_iso = "2026-03-07T16:54:00Z"

    async def fake_compute_verdicts_fn(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "NVDA",
                        "verdict": "buy",
                        "confidence": 0.82,
                        "expected_return": 0.11,
                        "generated_at": now_iso,
                        "source": ["judge_route", "news_feed_snapshot"],
                        "debug_payload": {
                            "news": [
                                {
                                    "title": "NVIDIA demand accelerates",
                                    "source": "Reuters",
                                    "ts": "2026-03-07T12:54:00Z",
                                    "sent": 0.7,
                                }
                            ]
                        },
                        "attachments": [
                            {
                                "title": "phase_scores",
                                "confidence": 0.74,
                                "generated_at": now_iso,
                            }
                        ],
                    }
                ],
                "count": 1,
                "generated_at": now_iso,
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "load_json",
        lambda _key: {"schema_version": "decision_journal_v1", "entries": []},
    )
    monkeypatch.setattr(
        judge_endpoint_service,
        "save_json",
        lambda key, payload, source=None, version="v1": Path("runtime/data") / f"{key}.json",
    )
    monkeypatch.setattr(
        judge_endpoint_service,
        "_persist_immutable_decision_journal_entries",
        lambda entries, generated_at: {
            "status": "persisted",
            "storage_key_prefix": "decision_journal/entries",
            "schema_version": "decision_journal_v1",
            "path_prefix": "runtime/data/decision_journal/entries",
            "persisted_count": len(entries),
            "existing_count": 0,
            "failed_count": 0,
        },
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_verdicts_payload(
            limit=1,
            min_confidence=0.3,
            ticker=["NVDA"],
            sort_by="confidence",
            sort_order="desc",
            profile="balanced",
            debug=False,
            debug_full=False,
            x_debug_token=None,
            compute_verdicts_fn=fake_compute_verdicts_fn,
        )
    )

    explainability = payload["data"]["explainability"]
    graph = explainability["graph"]
    assert any(node["kind"] == "verdict" and node["ticker"] == "NVDA" for node in graph["nodes"])
    assert any(node["kind"] == "news_item" for node in graph["nodes"])
    assert any(node["kind"] == "attachment" for node in graph["nodes"])
    assert any(edge["relationship"] == "supports" and edge["weight"] > 0 for edge in graph["edges"])
    trace = explainability["source_traceability"][0]
    assert trace["ticker"] == "NVDA"
    assert any(source["kind"] == "news_item" for source in trace["supporting_sources"])
    assert any(source["kind"] == "attachment" for source in trace["supporting_sources"])
    assert explainability["stats"]["avg_source_weight"] > 0


def test_judge_verdicts_payload_counts_invalid_source_links(monkeypatch):
    now_iso = "2026-03-07T16:54:00Z"

    async def fake_compute_verdicts_fn(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "NVDA",
                        "verdict": "buy",
                        "confidence": 0.82,
                        "expected_return": 0.11,
                        "generated_at": now_iso,
                        "source": ["judge_route", "news_feed_snapshot"],
                        "debug_payload": {
                            "news": [
                                {
                                    "title": "NVIDIA demand accelerates",
                                    "source": "Reuters",
                                    "ts": "2026-03-07T12:54:00Z",
                                    "sent": 0.7,
                                    "url": "https://example.com/nvda-demand",
                                },
                                {
                                    "title": "Malformed trace source",
                                    "source": "Blog",
                                    "ts": "2026-03-07T11:54:00Z",
                                    "sent": 0.2,
                                    "url": "not-a-valid-url",
                                },
                            ]
                        },
                    }
                ],
                "count": 1,
                "generated_at": now_iso,
            },
            "freshness": now_iso,
        }

    monkeypatch.setattr(
        judge_endpoint_service,
        "load_json",
        lambda _key: {"schema_version": "decision_journal_v1", "entries": []},
    )
    monkeypatch.setattr(
        judge_endpoint_service,
        "save_json",
        lambda key, payload, source=None, version="v1": Path("runtime/data") / f"{key}.json",
    )
    monkeypatch.setattr(
        judge_endpoint_service,
        "_persist_immutable_decision_journal_entries",
        lambda entries, generated_at: {
            "status": "persisted",
            "storage_key_prefix": "decision_journal/entries",
            "schema_version": "decision_journal_v1",
            "path_prefix": "runtime/data/decision_journal/entries",
            "persisted_count": len(entries),
            "existing_count": 0,
            "failed_count": 0,
        },
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_verdicts_payload(
            limit=1,
            min_confidence=0.3,
            ticker=["NVDA"],
            sort_by="confidence",
            sort_order="desc",
            profile="balanced",
            debug=False,
            debug_full=False,
            x_debug_token=None,
            compute_verdicts_fn=fake_compute_verdicts_fn,
        )
    )

    explainability = payload["data"]["explainability"]
    trace = explainability["source_traceability"][0]
    links = {source["label"]: source for source in trace["supporting_sources"]}

    assert explainability["stats"]["broken_source_count"] == 1
    assert links["NVIDIA demand accelerates"]["url"] == "https://example.com/nvda-demand"
    assert links["NVIDIA demand accelerates"]["link_status"] == "ok"
    assert links["Malformed trace source"]["link_status"] == "invalid"


def test_judge_verdicts_payload_applies_personal_policy_guardrails(monkeypatch):
    now_iso = "2026-03-07T16:54:00Z"

    async def fake_compute_verdicts_fn(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "TSLA",
                        "verdict": "buy",
                        "confidence": 0.78,
                        "expected_return": 0.14,
                        "risk_level": "high",
                        "summary": ["Momentum is strong but volatile."],
                        "scenarios": [],
                        "risks": ["valuation"],
                        "impacts": {},
                        "actions": ["buy incrementally"],
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
                "source": ["judge_route", "tests"],
            },
            "freshness": now_iso,
        }

    def fake_load_json(key):
        if key == judge_endpoint_service.JUDGE_POLICY_STORAGE_KEY:
            return {
                "policy_id": "personal-default",
                "policy_version": "2026-03-11T09:00:00Z",
                "updated_at": "2026-03-11T09:00:00Z",
                "excluded_tickers": ["TSLA"],
                "blocked_actions": ["buy"],
                "max_risk_level": "medium",
            }
        return {"schema_version": "decision_journal_v1", "entries": []}

    monkeypatch.setattr(judge_endpoint_service, "load_json", fake_load_json)
    monkeypatch.setattr(
        judge_endpoint_service,
        "save_json",
        lambda key, payload, source=None, version="v1": Path("runtime/data") / f"{key}.json",
    )
    monkeypatch.setattr(
        judge_endpoint_service,
        "_persist_immutable_decision_journal_entries",
        lambda entries, generated_at: {
            "status": "persisted",
            "storage_key_prefix": "decision_journal/entries",
            "schema_version": "decision_journal_v1",
            "path_prefix": "runtime/data/decision_journal/entries",
            "persisted_count": len(entries),
            "existing_count": 0,
            "failed_count": 0,
        },
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_verdicts_payload(
            limit=1,
            min_confidence=0.3,
            ticker=["TSLA"],
            sort_by="confidence",
            sort_order="desc",
            profile="balanced",
            debug=False,
            debug_full=False,
            x_debug_token=None,
            compute_verdicts_fn=fake_compute_verdicts_fn,
        )
    )

    verdict = payload["data"]["verdicts"][0]
    guardrails = verdict["policy_guardrails"]
    assert verdict["verdict"] == "hold"
    assert verdict["action"] == "hold"
    assert payload["data"]["policy_guardrails"]["summary"] == {
        "verdict_count": 1,
        "violations_count": 3,
        "downgraded_count": 1,
    }
    assert guardrails["status"] == "violated"
    assert guardrails["original_action"] == "buy"
    assert guardrails["effective_action"] == "hold"
    assert {violation["code"] for violation in guardrails["violations"]} == {
        "ticker_excluded",
        "action_blocked",
        "risk_above_limit",
    }
    assert "policy_guardrail_violation" in payload["data"]["warnings"]
    assert "judge_policy_guardrail_projection_v1" in payload["data"]["source"]


def test_judge_verdicts_payload_respects_stored_outcome_feedback(monkeypatch):
    now_iso = "2026-03-07T16:54:00Z"
    judge_decision_id = "judge_c28e370c4d647688"
    saved = {}

    async def fake_compute_verdicts_fn(**_kwargs):
        return {
            "ok": True,
            "data": {
                "verdicts": [
                    {
                        "ticker": "AAPL",
                        "verdict": "buy",
                        "confidence": 0.81,
                        "expected_return": 0.05,
                        "score": 0.72,
                        "horizon": "1w",
                    }
                ],
                "count": 1,
                "generated_at": now_iso,
                "source": ["judge_route", "tests"],
            },
            "freshness": now_iso,
        }

    def fake_load_json(key):
        if key == judge_endpoint_service.DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY:
            return {
                "records": [
                    {
                        "record_id": "rec-1",
                        "decision_id": judge_decision_id,
                        "horizon": "1w",
                        "status": "resolved",
                        "outcome": "hit",
                        "actual_return": 0.041,
                        "recorded_at": "2026-03-08T09:00:00Z",
                    },
                ]
            }

        return {
            "schema_version": "decision_journal_v1",
            "entries": [],
        }

    def fake_save_json(key, payload, source=None, version="v1"):
        saved["key"] = key
        saved["payload"] = payload
        return Path("runtime/data/decision_journal.json")

    monkeypatch.setattr(judge_endpoint_service, "load_json", fake_load_json)
    monkeypatch.setattr(judge_endpoint_service, "save_json", fake_save_json)

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

    outcome_feedback = payload["data"]["decision_journal"]["entries"][0]["outcome_feedback"]
    journal_entry = payload["data"]["decision_journal"]["entries"][0]
    assert journal_entry["decision_id"] == judge_decision_id
    assert outcome_feedback["status"] == "in_progress"
    assert outcome_feedback["latest_feedback_at"] == "2026-03-08T09:00:00Z"
    assert outcome_feedback["next_checkpoint"]["horizon"] == "1d"
    checkpoints = {
        str(c["horizon"]): c
        for c in outcome_feedback.get("checkpoints", [])
        if isinstance(c, dict)
    }
    assert checkpoints["1w"]["status"] == "resolved"
    assert checkpoints["1w"]["outcome"] == "hit"
    assert checkpoints["1w"]["actual_return"] == 0.041
    assert payload["data"]["decision_journal"]["feedback_loop"]["pending_feedback_records"] == 2


def test_judge_verdicts_payload_does_not_rewrite_existing_immutable_snapshot(monkeypatch, tmp_path):
    now_iso = "2026-03-07T16:54:00Z"
    journal_state = {
        "schema_version": "decision_journal_v1",
        "entries": [],
    }
    immutable_writes = []

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

    def fake_load_json(key):
        if key == judge_endpoint_service.DECISION_JOURNAL_STORAGE_KEY:
            return dict(journal_state)
        return {"records": []}

    def fake_save_json(key, payload, source=None, version="v1"):
        if key == judge_endpoint_service.DECISION_JOURNAL_STORAGE_KEY:
            journal_state["entries"] = list(payload.get("entries") or [])
            return Path("runtime/data/decision_journal.json")

        decision_id = key.rsplit("/", 1)[-1]
        path = tmp_path / "decision_journal" / "entries" / f"{decision_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    **payload,
                    "source": source or [],
                    "version": version,
                }
            ),
            encoding="utf-8",
        )
        immutable_writes.append(key)
        return path

    monkeypatch.setattr(judge_endpoint_service, "load_json", fake_load_json)
    monkeypatch.setattr(judge_endpoint_service, "save_json", fake_save_json)
    monkeypatch.setattr(
        judge_endpoint_service,
        "_decision_journal_entry_path",
        lambda decision_id: tmp_path / "decision_journal" / "entries" / f"{decision_id}.json",
    )

    first_payload = asyncio.run(
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
    decision_id = first_payload["data"]["decision_journal"]["entries"][0]["decision_id"]
    assert first_payload["data"]["decision_journal"]["store"]["immutable_store"]["persisted_count"] == 1

    second_payload = asyncio.run(
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

    assert immutable_writes == [f"decision_journal/entries/{decision_id}"]
    assert second_payload["data"]["decision_journal"]["store"]["immutable_store"] == {
        "status": "already_persisted",
        "storage_key_prefix": "decision_journal/entries",
        "schema_version": "decision_journal_v1",
        "path_prefix": "runtime/data/decision_journal/entries",
        "persisted_count": 0,
        "existing_count": 1,
        "failed_count": 0,
    }


def test_judge_decision_journal_payload_filters_and_applies_feedback(monkeypatch):
    def fake_load_json(key):
        if key == judge_endpoint_service.DECISION_JOURNAL_STORAGE_KEY:
            return {
                "schema_version": "decision_journal_v1",
                "entries": [
                    {
                        "decision_id": "judge_demo_aapl",
                        "captured_at": "2026-03-08T00:00:00Z",
                        "profile": "balanced",
                        "outcome_feedback": {
                            "schema_version": "decision_outcome_feedback_v1",
                            "status": "pending",
                            "checkpoints": [
                                {
                                    "horizon": "1d",
                                    "status": "pending",
                                    "due_at": "2026-03-09T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                                {
                                    "horizon": "1w",
                                    "status": "pending",
                                    "due_at": "2026-03-15T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                                {
                                    "horizon": "1m",
                                    "status": "pending",
                                    "due_at": "2026-04-07T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                            ],
                        },
                    },
                    {
                        "decision_id": "judge_demo_msft",
                        "captured_at": "2026-03-07T00:00:00Z",
                        "profile": "balanced",
                        "outcome_feedback": {
                            "schema_version": "decision_outcome_feedback_v1",
                            "status": "pending",
                            "checkpoints": [
                                {
                                    "horizon": "1d",
                                    "status": "pending",
                                    "due_at": "2026-03-08T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                                {
                                    "horizon": "1w",
                                    "status": "pending",
                                    "due_at": "2026-03-14T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                                {
                                    "horizon": "1m",
                                    "status": "pending",
                                    "due_at": "2026-04-06T00:00:00Z",
                                    "record_mode": "separate_record",
                                },
                            ],
                        },
                    },
                ],
            }
        if key == judge_endpoint_service.DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY:
            return {
                "records": [
                    {
                        "decision_id": "judge_demo_aapl",
                        "horizon": "1w",
                        "status": "resolved",
                        "outcome": "miss",
                        "actual_return": -0.021,
                        "recorded_at": "2026-03-09T06:00:00Z",
                    }
                ]
            }
        return {}

    monkeypatch.setattr(judge_endpoint_service, "load_json", fake_load_json)

    payload = asyncio.run(
        judge_endpoint_service.get_judge_decision_journal_payload(
            decision_id="judge_demo_aapl",
            status_filter="in_progress",
            limit=10,
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["data"]["schema_version"] == "decision_journal_v1"
    assert payload["data"]["count"] == 2
    assert payload["data"]["filtered_count"] == 1
    assert payload["data"]["returned_count"] == 1
    entry = payload["data"]["entries"][0]
    assert entry["decision_id"] == "judge_demo_aapl"
    assert entry["outcome_feedback"]["status"] == "in_progress"
    assert entry["outcome_feedback"]["checkpoints"][1]["status"] == "resolved"
    assert entry["outcome_feedback"]["checkpoints"][1]["actual_return"] == -0.021


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


def test_judge_decision_outcome_feedback_persists_append_only(monkeypatch):
    store = {}

    def fake_load_json(key):
        if key != judge_endpoint_service.DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY:
            return None
        return {"records": list(store.get("records", []))}

    def fake_save_json(key, payload, source=None, version="v1"):
        assert key == judge_endpoint_service.DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY
        store["records"] = payload.get("records", [])
        return Path("/tmp/judge_decision_outcome_feedback_records.json")

    monkeypatch.setattr(judge_endpoint_service, "load_json", fake_load_json)
    monkeypatch.setattr(judge_endpoint_service, "save_json", fake_save_json)

    first = asyncio.run(
        judge_endpoint_service.append_judge_decision_outcome_feedback(
            feedback={
                "decision_id": "judge_1",
                "horizon": "1d",
                "status": "resolved",
                "outcome": "hit",
                "actual_return": 0.015,
            }
        )
    )
    second = asyncio.run(
        judge_endpoint_service.append_judge_decision_outcome_feedback(
            feedback={
                "decision_id": "judge_2",
                "horizon": "1w",
                "status": "resolved",
                "outcome": "miss",
                "actual_return": -0.013,
            }
        )
    )

    assert first["status"] == "ok"
    assert first["data"]["stored_records"] == 1
    assert second["status"] == "ok"
    assert second["data"]["stored_records"] == 2
    assert (
        first["data"]["store"]["storage_key"]
        == judge_endpoint_service.DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY
    )
    assert second["data"]["stored_records"] == len(store["records"])
    assert store["records"][-1]["decision_id"] == "judge_2"
