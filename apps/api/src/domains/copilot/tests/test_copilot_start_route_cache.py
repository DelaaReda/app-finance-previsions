from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.copilot.api import copilot as copilot_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(copilot_route.router, prefix="/api")
    return TestClient(app)


def _payload(summary: str) -> dict:
    return {
        "daily_brief": {
            "summary": summary,
            "market_sentiment": "NEUTRAL",
            "generated_at": "2026-03-19T10:00:00Z",
            "freshness": "2026-03-19T10:00:00Z",
            "source": ["copilot_start_test"],
        },
        "entry_points": [
            {"id": "brief_of_day", "kind": "open", "target": "/brief/daily"},
            {"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"},
            {"id": "open_copilot", "kind": "open", "target": "/copilot"},
        ],
        "copilot_start": {
            "brief_of_day": {
                "summary": summary,
                "market_sentiment": "NEUTRAL",
                "generated_at": "2026-03-19T10:00:00Z",
                "freshness": "2026-03-19T10:00:00Z",
                "source": ["copilot_start_test"],
            },
            "ask": [{"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"}],
            "open": [{"id": "open_copilot", "kind": "open", "target": "/copilot"}],
        },
    }


def test_copilot_start_repeated_calls_return_cache_hit(monkeypatch):
    copilot_route._COPILOT_START_CACHE.clear()
    calls = {"count": 0}

    async def fake_build_copilot_start_endpoint_payload(**_kwargs):
        calls["count"] += 1
        payload = _payload("Fresh market brief.")
        return {
            **payload["copilot_start"],
            "generated_at": "2026-03-19T10:00:00Z",
            "freshness": "2026-03-19T10:00:00Z",
            "source": ["copilot_start_test"],
            "filters_applied": {"tickers": ["NVDA"]},
            "stats": {"ask_count": 1, "open_count": 1},
            "warnings": [],
        }

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_copilot_start_endpoint_payload",
        fake_build_copilot_start_endpoint_payload,
    )

    client = _client()
    first = client.get("/api/copilot/start?tickers=nvda")
    second = client.get("/api/copilot/start?tickers=nvda")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1

    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["cache"] == {"hit": False, "age_seconds": 0.0, "ttl_seconds": copilot_route.COPILOT_START_CACHE_TTL_SECONDS}
    assert second_data["cache"]["hit"] is True
    assert second_data["cache"]["ttl_seconds"] == copilot_route.COPILOT_START_CACHE_TTL_SECONDS
    assert "copilot_start_cache_hit" in (second_data.get("source") or [])


def test_copilot_start_debug_bypasses_cache(monkeypatch):
    copilot_route._COPILOT_START_CACHE.clear()
    calls = {"count": 0}

    async def fake_build_copilot_start_endpoint_payload(**_kwargs):
        calls["count"] += 1
        payload = _payload(f"Fresh market brief #{calls['count']}")
        return {
            **payload["copilot_start"],
            "generated_at": "2026-03-19T10:00:00Z",
            "freshness": "2026-03-19T10:00:00Z",
            "source": ["copilot_start_test"],
            "filters_applied": {"tickers": ["NVDA"]},
            "stats": {"ask_count": 1, "open_count": 1},
            "warnings": [],
        }

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_copilot_start_endpoint_payload",
        fake_build_copilot_start_endpoint_payload,
    )

    client = _client()
    cached = client.get("/api/copilot/start?tickers=nvda")
    debug = client.get("/api/copilot/start?tickers=nvda&debug=true")
    replay = client.get("/api/copilot/start?tickers=nvda")

    assert cached.status_code == 200
    assert debug.status_code == 200
    assert replay.status_code == 200
    assert calls["count"] == 2

    cached_data = cached.json()["data"]
    debug_data = debug.json()["data"]
    replay_data = replay.json()["data"]
    assert cached_data["brief_of_day"]["summary"] == "Fresh market brief #1"
    assert debug_data["brief_of_day"]["summary"] == "Fresh market brief #2"
    assert replay_data["brief_of_day"]["summary"] == "Fresh market brief #1"
    assert debug_data["cache"]["hit"] is False
    assert "copilot_start_cache_hit" not in (debug_data.get("source") or [])


def test_copilot_start_route_prefers_shared_endpoint_builder(monkeypatch):
    copilot_route._COPILOT_START_CACHE.clear()
    calls = {"endpoint": 0, "context": 0}

    async def fake_build_copilot_start_endpoint_payload(**_kwargs):
        calls["endpoint"] += 1
        return {
            "brief_of_day": {
                "summary": "Shared contract payload.",
                "market_sentiment": "NEUTRAL",
                "generated_at": "2026-03-19T10:00:00Z",
                "freshness": "2026-03-19T10:00:00Z",
                "source": ["copilot_start_endpoint_service"],
            },
            "ask": [{"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"}],
            "open": [{"id": "open_copilot", "kind": "open", "target": "/copilot"}],
            "source": ["copilot_start_endpoint_service"],
        }

    async def fake_build_context_payload(**_kwargs):
        calls["context"] += 1
        return _payload("Legacy context payload.")

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_copilot_start_endpoint_payload",
        fake_build_copilot_start_endpoint_payload,
    )
    monkeypatch.setattr(copilot_route.copilot_service, "build_context_payload", fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/start?tickers=nvda")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["brief_of_day"]["summary"] == "Shared contract payload."
    assert calls == {"endpoint": 1, "context": 0}


def test_copilot_context_repeated_calls_return_cache_hit(monkeypatch):
    copilot_route._COPILOT_CONTEXT_CACHE.clear()
    calls = {"count": 0}

    async def fake_build_context_payload(**_kwargs):
        calls["count"] += 1
        return _payload(f"Fresh context #{calls['count']}")

    monkeypatch.setattr(copilot_route.copilot_service, "build_context_payload", fake_build_context_payload)

    client = _client()
    first = client.get("/api/copilot/context?tickers=nvda")
    second = client.get("/api/copilot/context?tickers=nvda")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1

    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["cache"] == {"hit": False, "age_seconds": 0.0, "ttl_seconds": copilot_route.COPILOT_CONTEXT_CACHE_TTL_SECONDS}
    assert second_data["cache"]["hit"] is True
    assert second_data["cache"]["ttl_seconds"] == copilot_route.COPILOT_CONTEXT_CACHE_TTL_SECONDS
    assert "copilot_context_cache_hit" in (second_data.get("source") or [])
