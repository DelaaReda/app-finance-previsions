from __future__ import annotations

import re

from src.services import service_standard


def test_utc_now_iso_uses_z_suffix():
    now_iso = service_standard.utc_now_iso()
    assert now_iso.endswith("Z")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", now_iso)


def test_safe_int_is_bool_safe():
    assert service_standard.safe_int(True, 7) == 7
    assert service_standard.safe_int("12", 0) == 12
    assert service_standard.safe_int("x", 9) == 9


def test_safe_float_supports_default():
    assert service_standard.safe_float("0.45") == 0.45
    assert service_standard.safe_float(False, 1.2) == 1.2
    assert service_standard.safe_float("x", 2.5) == 2.5
    assert service_standard.safe_float("x") is None


def test_source_helpers_normalize_and_deduplicate():
    payload = {"source": "judge_route"}
    service_standard.append_source_tag(payload, "cache_hit", default_source="judge_route")
    service_standard.append_source_tag(payload, "cache_hit", default_source="judge_route")
    assert payload["source"] == ["judge_route", "cache_hit"]


def test_service_response_derives_freshness_from_generated_at():
    data = {"generated_at": "2026-02-28T00:00:00Z"}
    envelope = service_standard.service_response(data)
    assert envelope["ok"] is True
    assert envelope["data"] == data
    assert envelope["freshness"] == "2026-02-28T00:00:00Z"


def test_never_empty_payload_adds_required_metadata():
    payload = service_standard.never_empty_payload(
        base={"count": 0},
        default_source="forecasts_service",
        error="boom",
        message="fallback",
        generated_at="2026-02-28T00:00:00Z",
    )
    assert payload["generated_at"] == "2026-02-28T00:00:00Z"
    assert payload["source"] == ["forecasts_service"]
    assert payload["error"] == "boom"
    assert payload["message"] == "fallback"


def test_unwrap_storage_payload_supports_data_and_payload_wrappers():
    assert service_standard.unwrap_storage_payload({"data": {"k": 1}}) == {"k": 1}
    assert service_standard.unwrap_storage_payload({"payload": {"k": 2}}) == {"k": 2}
    raw = {"k": 3}
    assert service_standard.unwrap_storage_payload(raw) == raw
