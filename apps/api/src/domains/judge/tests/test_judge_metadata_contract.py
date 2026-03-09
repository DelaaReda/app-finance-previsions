from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application import judge_endpoint_service


def test_judge_verdicts_payload_exposes_stable_metadata(monkeypatch):
    now_iso = "2026-03-07T16:54:00Z"
    saved = {}

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
        saved["key"] = key
        saved["payload"] = payload
        saved["source"] = source
        saved["version"] = version
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
    assert saved["key"] == "decision_journal"
    assert saved["source"] == ["judge_endpoint_service", "decision_journal_store_v1"]
    assert saved["version"] == "decision_journal_v1"
    assert saved["payload"]["append_only"] is True
    assert saved["payload"]["outcomes_update_mode"] == "separate_records"
    assert saved["payload"]["entries"][0]["decision_id"] == entry["decision_id"]


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
