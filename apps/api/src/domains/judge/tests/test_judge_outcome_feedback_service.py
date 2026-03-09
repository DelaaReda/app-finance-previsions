from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from typing import Any, Dict, List

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domains.judge.application import judge_endpoint_service  # noqa: E402


def test_get_judge_decision_outcome_feedback_service_filters_records(monkeypatch):
    records: List[Dict[str, Any]] = [
        {
            "record_id": "r1",
            "decision_id": "judge_1",
            "horizon": "1d",
            "status": "resolved",
            "recorded_at": "2026-03-08T12:00:00Z",
        },
        {
            "record_id": "r2",
            "decision_id": "judge_2",
            "horizon": "1w",
            "status": "open",
            "recorded_at": "2026-03-09T12:00:00Z",
        },
    ]

    monkeypatch.setattr(
        judge_endpoint_service,
        "_load_outcome_feedback_records",
        lambda: records,
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_decision_outcome_feedback(
            decision_id="judge_2", horizon="1w", status_filter=None, limit=1
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["data"]["filtered_count"] == 1
    assert payload["data"]["returned_count"] == 1
    assert payload["data"]["records"][0]["record_id"] == "r2"


def test_get_judge_decision_outcome_feedback_service_invalid_horizon_returns_degraded():
    payload = asyncio.run(
        judge_endpoint_service.get_judge_decision_outcome_feedback(
            decision_id="judge_2", horizon="bad", status_filter=None, limit=1
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert payload["data"]["filtered_count"] == 0
    assert payload["data"]["records"] == []


def test_get_judge_decision_outcome_feedback_service_normalizes_legacy_status_filters(
    monkeypatch,
):
    records: List[Dict[str, Any]] = [
        {
            "record_id": "r1",
            "decision_id": "judge_1",
            "horizon": "1d",
            "status": "recorded",
            "recorded_at": "2026-03-08T12:00:00Z",
        }
    ]

    monkeypatch.setattr(
        judge_endpoint_service,
        "_load_outcome_feedback_records",
        lambda: records,
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_decision_outcome_feedback(
            decision_id="judge_1",
            horizon="1d",
            status_filter="in_progress",
            limit=5,
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["data"]["filtered_count"] == 1
    assert payload["data"]["records"][0]["status"] == "recorded"


def test_append_judge_decision_outcome_feedback_defaults_to_resolved_when_measurement_present(
    monkeypatch,
):
    store: Dict[str, Any] = {}

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

    payload = asyncio.run(
        judge_endpoint_service.append_judge_decision_outcome_feedback(
            feedback={
                "decision_id": "judge_3",
                "horizon": "1m",
                "outcome": "hit",
                "actual_return": 0.022,
            }
        )
    )

    assert payload["status"] == "ok"
    assert payload["data"]["feedback"]["status"] == "resolved"
    assert store["records"][-1]["status"] == "resolved"
