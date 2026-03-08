from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from platform.routers import health


def test_runtime_rate_limit_snapshot_reads_active_cooldowns(tmp_path, monkeypatch):
    now = int(time.time())
    monkeypatch.setenv("FC_ROLE_STATE_DIR", str(tmp_path))
    (tmp_path / "planner.rate_limit_gate_cache").write_text(f"{now+90}|planner throttling")
    (tmp_path / "dev.rate_limit_gate_cache").write_text(f"{now-10}|expired")

    payload = health._runtime_rate_limit_snapshot()

    assert payload["active_count"] == 1
    assert payload["cooldowns"]
    active = payload["active_cooldowns"]
    assert active[0]["actor"] == "planner"
    assert active[0]["reason"] == "planner throttling"
    assert active[0]["active"] is True


def test_ingestion_health_endpoint_returns_freshness_payload(monkeypatch):
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data_freshness_ttl = {
        "forecasts": 24 * 3600,
        "news_feed": 30 * 60,
        "brief_weekly": 24 * 3600,
        "macro_series": 7 * 24 * 3600,
        "stocks": 24 * 3600,
        "backtests": 30 * 24 * 3600,
        "brief_daily": 24 * 3600,
    }

    def fake_load_json(filename: str):
        if filename == "forecasts":
            return {"generated_at": now_iso, "last_update": now_iso}
        if filename == "forecasts.json":
            return {"generated_at": now_iso, "last_update": now_iso}
        return {"generated_at": now_iso, "last_update": now_iso}

    def fake_freshness(payload, ttl_seconds, now=None):
        if payload is None:
            return {
                "timestamp": None,
                "age_seconds": None,
                "age_minutes": None,
                "ttl_seconds": ttl_seconds,
                "status": "missing",
                "is_fresh": False,
            }
        return {
            "timestamp": now_iso,
            "age_seconds": 0.0,
            "age_minutes": 0.0,
            "ttl_seconds": ttl_seconds,
            "status": "fresh",
            "is_fresh": True,
        }

    monkeypatch.setattr(health, "_load_json_compat", fake_load_json)
    source_status = [
        health._ingestion_source_status(
            source_name=source_name,
            file_key=file_key,
            ttl_key=ttl_key,
            freshness_payload=fake_freshness,
            data_freshness_ttl=data_freshness_ttl,
            now=datetime.now(timezone.utc),
        )
        for source_name, file_key, ttl_key in health.INGESTION_SOURCE_OBSERVABILITY
    ]
    assert all(item["status"] == "fresh" for item in source_status)
    assert all(item["errors"] == [] for item in source_status)
    assert len(source_status) == 7
    assert {entry["source"] for entry in source_status} == {
        "forecasts",
        "news",
        "macro_series",
        "stocks",
        "backtests",
        "brief_weekly",
        "brief_daily",
    }


def test_health_and_status_routes_share_canonical_contract(monkeypatch):
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def fake_load_json(filename: str):
        return {"generated_at": now_iso, "last_update": now_iso, "filename": filename}

    monkeypatch.setattr(health, "_load_json_compat", fake_load_json)

    router = health.create_health_router(
        ok_response=lambda data: {"ok": True, "data": data},
        freshness_payload=lambda payload, ttl_seconds, now=None: {
            "timestamp": now_iso,
            "age_seconds": 0.0,
            "age_minutes": 0.0,
            "ttl_seconds": ttl_seconds,
            "status": "fresh",
            "is_fresh": True,
        },
        frontend_runtime_config=lambda: {"enabled": True},
        data_freshness_ttl={
            "forecasts": 24 * 3600,
            "news_feed": 30 * 60,
            "brief_weekly": 24 * 3600,
            "macro_series": 7 * 24 * 3600,
            "stocks": 24 * 3600,
            "backtests": 30 * 24 * 3600,
            "brief_daily": 24 * 3600,
        },
    )
    endpoints = {route.path: route.endpoint for route in router.routes}

    for path, source_tag in (("/api/health", "api_health"), ("/api/status", "api_status")):
        payload = asyncio.run(endpoints[path]())

        assert payload["ok"] is True
        data = payload["data"]
        assert data["status"] == "ok"
        assert data["service_status"] == "ok"
        assert data["backend_up"] is True
        assert data["freshness"] == data["generated_at"]
        assert data["last_update"] == data["generated_at"]
        assert data["filters_applied"] == {}
        assert "warnings" in data
        assert data["source"] == [source_tag]
        assert data["stats"]["checked_sources"] == 4


def test_status_route_returns_never_empty_fallback_on_payload_error(monkeypatch):
    def boom(_: str):
        raise RuntimeError("snapshot read failed")

    monkeypatch.setattr(health, "_load_json_compat", boom)

    router = health.create_health_router(
        ok_response=lambda data: {"ok": True, "data": data},
        freshness_payload=lambda payload, ttl_seconds, now=None: {},
        frontend_runtime_config=lambda: {"enabled": True},
        data_freshness_ttl={
            "forecasts": 24 * 3600,
            "news_feed": 30 * 60,
            "brief_weekly": 24 * 3600,
            "macro_series": 7 * 24 * 3600,
            "stocks": 24 * 3600,
            "backtests": 30 * 24 * 3600,
            "brief_daily": 24 * 3600,
        },
    )
    endpoints = {route.path: route.endpoint for route in router.routes}
    payload = asyncio.run(endpoints["/api/status"]())

    assert payload["ok"] is True
    data = payload["data"]
    assert data["status"] == "degraded"
    assert data["service_status"] == "degraded"
    assert data["source"] == ["api_status", "critical_error_fallback"]
    assert data["warnings"] == ["status_payload_failed"]
    assert data["error"] == "snapshot read failed"
    assert data["message"] == "status endpoint fallback (never-empty contract)."
