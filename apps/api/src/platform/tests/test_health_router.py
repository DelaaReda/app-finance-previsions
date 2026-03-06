from __future__ import annotations

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
