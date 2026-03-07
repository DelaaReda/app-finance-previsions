from __future__ import annotations

from platform.legacy.services import service_standard


def test_service_response_with_metadata_keeps_nominal_contract_stable():
    payload = service_standard.service_response_with_metadata(
        {
            "portfolio_value": 123.45,
            "generated_at": "2026-03-07T23:00:00Z",
        },
        default_source="batch_28_dev_03_smoke",
    )

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["freshness"] == "2026-03-07T23:00:00Z"
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["error"] is None
    assert payload["data"]["warnings"] == []
    assert payload["data"]["freshness"] == "2026-03-07T23:00:00Z"
    assert "batch_28_dev_03_smoke" in payload["data"]["source"]
    assert "metadata_contract_v1" in payload["data"]["source"]


def test_service_response_with_metadata_normalizes_timeout_and_partial_payload():
    payload = service_standard.service_response_with_metadata(
        {
            "generated_at": "2026-03-07T23:00:00Z",
            "freshness": "error",
            "warnings": "partial payload missing macro block",
        },
        default_source="batch_28_dev_03_smoke",
        error="timeout",
    )

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert payload["error"] == "timeout"
    assert payload["freshness"] == "2026-03-07T23:00:00Z"
    assert payload["data"]["status"] == "degraded"
    assert payload["data"]["error"] == "timeout"
    assert payload["data"]["warnings"] == ["partial payload missing macro block"]
    assert payload["data"]["freshness"] == "2026-03-07T23:00:00Z"
    assert "batch_28_dev_03_smoke" in payload["data"]["source"]
    assert "metadata_contract_v1" in payload["data"]["source"]
