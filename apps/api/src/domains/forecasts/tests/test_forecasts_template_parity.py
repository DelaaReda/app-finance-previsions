from __future__ import annotations

import asyncio
import time

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import forecasts as forecasts_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(forecasts_route.router)
    return TestClient(app)


def test_forecasts_query_validation_rejects_invalid_sort_order():
    client = _client()
    resp = client.get("/forecasts?sort_order=foo")
    assert resp.status_code == 422


def test_forecasts_openapi_exposes_enum_params_and_response_schema():
    client = _client()
    payload = client.get("/openapi.json").json()
    op = payload["paths"]["/forecasts"]["get"]
    params = {p["name"]: p.get("schema", {}) for p in op.get("parameters", [])}

    assert params["sort_order"].get("enum") == ["asc", "desc"]
    assert params["sort_by"].get("enum") == [
        "score",
        "confidence",
        "expected_return",
        "timestamp",
        "risk_level",
    ]
    response_schema = op["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema, "Forecasts 200 response schema must not be empty."

    components = payload.get("components", {}).get("schemas", {})
    row_schema = components.get("ForecastContractDto", {})
    row_props = row_schema.get("properties", {})
    required_keys = {
        "action",
        "direction",
        "confidence",
        "horizon",
        "why",
        "risk_flag",
        "generated_at",
        "freshness_status",
        "forecast_id",
        "provider_chain",
        "fallback_used",
        "latency_ms",
        "freshness_age",
    }
    assert required_keys.issubset(set(row_props.keys()))


def test_forecasts_cache_hit_and_debug_bypass(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["test_snapshot"],
        "rows": [
            {
                "ticker": "aapl",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.9,
                "confidence": 0.7,
                "expected_return": 0.03,
                "risk_level": "high",
                "timestamp": "2026-02-27T00:00:00Z",
            }
        ],
    }

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)
    client = _client()

    path = "/forecasts?asset_type=equity&horizon=1w&sort_by=score&sort_order=desc&limit=10&offset=0"
    first = client.get(path)
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first_data["cache"]["hit"] is False

    second = client.get(path)
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["cache"]["hit"] is True
    assert "forecasts_cache_hit" in (second_data.get("source") or [])

    debug_resp = client.get(path + "&debug=true")
    assert debug_resp.status_code == 200
    debug_data = debug_resp.json()["data"]
    assert debug_data["cache"]["hit"] is False
    assert "forecasts_cache_hit" not in (debug_data.get("source") or [])
    assert isinstance(debug_data.get("debug_pipeline"), list)


def test_forecasts_contract_rows_include_required_keys(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["forecasts_job"],
        "rows": [
            {
                "ticker": "aapl",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.9,
                "confidence": 0.7,
                "expected_return": 0.03,
                "risk_level": "high",
                "timestamp": "2026-02-27T00:00:00Z",
                "model": "deepseek-v3",
            }
        ],
    }

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)
    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=1")
    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert payload["fallback_used"] is False
    assert "forecasts_live_compute" in (payload.get("source") or [])
    assert "mock" not in " ".join(payload.get("source") or []).lower()

    rows = payload.get("rows") or []
    assert len(rows) == 1
    row = rows[0]
    required_keys = {
        "action",
        "direction",
        "confidence",
        "horizon",
        "why",
        "risk_flag",
        "generated_at",
        "freshness_status",
        "forecast_id",
        "provider_chain",
        "fallback_used",
        "latency_ms",
        "freshness_age",
    }
    assert required_keys.issubset(set(row.keys()))
    assert row["forecast_id"]
    assert isinstance(row["provider_chain"], list)
    assert row["freshness_status"] in {"fresh", "stale", "unknown"}


def test_forecasts_normalizes_invalid_confidence_values(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["forecasts_job"],
        "rows": [
            {
                "ticker": "AAPL",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.9,
                "confidence": 0,
            },
            {
                "ticker": "MSFT",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.8,
                "confidence": 80,
            },
        ],
    }

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)
    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=10")
    assert resp.status_code == 200
    payload = resp.json()["data"]
    rows = payload.get("rows") or []
    assert len(rows) == 2
    assert rows[0]["confidence"] > 0
    assert rows[0]["confidence"] <= 1
    assert rows[1]["confidence"] > 0
    assert rows[1]["confidence"] <= 1
    assert payload["fallback_used"] is True
    assert payload["warnings"]


def test_forecasts_blocks_mock_source_in_nominal_mode(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["mock_forecasts_seed"],
        "rows": [
            {
                "ticker": "AAPL",
                "asset_type": "equity",
                "horizon": "1w",
                "confidence": 0.7,
            }
        ],
    }
    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)

    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=1")
    assert resp.status_code == 200
    payload = resp.json()["data"]

    assert payload["rows"] == []
    assert payload["fallback_used"] is True
    assert "mock_blocked_nominal" in (payload.get("source") or [])
    assert "forecasts_mock_gate_blocked" in (payload.get("source") or [])
    assert "mock" in str(payload.get("message", "")).lower()


def test_forecasts_fallback_is_explicit_on_internal_error(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    def _raise(_key):
        raise RuntimeError("boom")

    monkeypatch.setattr(forecasts_route, "load_json", _raise)
    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=1")
    assert resp.status_code == 200
    payload = resp.json()["data"]

    assert payload["rows"] == []
    assert payload["fallback_used"] is True
    assert "critical_error_fallback" in (payload.get("source") or [])
    obs = payload.get("observability") or {}
    assert obs.get("fallback_used") is True
    assert isinstance(obs.get("provider_chain"), list)


def test_forecasts_route_singleflight_computes_once(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()
    calls = {"load": 0}

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["test_snapshot"],
        "rows": [
            {
                "ticker": "AAPL",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.9,
                "confidence": 0.7,
                "expected_return": 0.03,
                "risk_level": "high",
                "timestamp": "2026-02-27T00:00:00Z",
            }
        ]
        * 500,
    }

    def fake_load_json(_key):
        calls["load"] += 1
        time.sleep(0.03)
        return snapshot

    monkeypatch.setattr(forecasts_route, "load_json", fake_load_json)

    app = FastAPI()
    app.include_router(forecasts_route.router)
    transport = httpx.ASGITransport(app=app)

    async def _run_parallel():
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            url = "/forecasts?asset_type=equity&horizon=1w&sort_by=score&sort_order=desc&limit=10&offset=0"
            responses = await asyncio.gather(*[client.get(url) for _ in range(4)])
            return responses

    responses = asyncio.run(_run_parallel())
    assert all(resp.status_code == 200 for resp in responses)
    assert calls["load"] == 1


def test_forecasts_marks_stale_snapshot_when_too_old(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    snapshot = {
        "generated_at": "2000-01-01T00:00:00Z",
        "last_update": "2000-01-01T00:00:00Z",
        "source": ["forecasts_job"],
        "rows": [
            {
                "ticker": "AAPL",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.8,
                "confidence": 0.6,
                "expected_return": 0.01,
                "risk_level": "medium",
                "timestamp": "2000-01-01T00:00:00Z",
            }
        ],
    }

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)
    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=1")
    assert resp.status_code == 200
    payload = resp.json()["data"]
    rows = payload.get("rows") or []
    assert len(rows) == 1

    assert payload["freshness_status"] == "stale"
    assert payload["freshness_age"] > 0
    assert rows[0]["freshness_status"] == "stale"
    assert rows[0]["freshness_age"] > 0


def test_forecasts_observability_aggregates_provider_chain_and_fallback(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["forecasts_job"],
        "rows": [
            {
                "ticker": "AAPL",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.9,
                "confidence": 0.8,
                "expected_return": 0.03,
                "risk_level": "high",
                "timestamp": "2026-02-27T00:00:00Z",
                "provider": "g4f",
                "model": "deepseek-v3",
                "latency_ms": 120.0,
                "fallback_used": False,
            },
            {
                "ticker": "MSFT",
                "asset_type": "equity",
                "horizon": "1w",
                "score": 0.7,
                "confidence": 0.6,
                "expected_return": -0.01,
                "risk_level": "medium",
                "timestamp": "2026-02-27T00:00:00Z",
                "provider_chain": ["g4f", "qwen"],
                "latency_ms": 180.0,
                "fallback_used": True,
            },
        ],
    }

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)
    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=10")
    assert resp.status_code == 200
    payload = resp.json()["data"]
    obs = payload.get("observability") or {}

    assert payload["fallback_used"] is True
    assert obs.get("fallback_used") is True
    assert isinstance(payload.get("provider_chain"), list)
    assert "g4f" in payload["provider_chain"]
    assert isinstance(obs.get("provider_chain"), list)
    assert "g4f" in obs["provider_chain"]
    assert obs.get("latency_ms", 0.0) > 0


def test_forecast_detail_lookup_supports_forecast_id_and_ticker(monkeypatch):
    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["forecasts_job"],
        "rows": [
            {
                "forecast_id": "AAPL:1w:2026-02-27T00:00:00Z",
                "ticker": "AAPL",
                "asset_type": "equity",
                "horizon": "1w",
                "confidence": 0.7,
            }
        ],
    }

    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)
    client = _client()

    by_id = client.get("/forecasts/AAPL:1w:2026-02-27T00:00:00Z")
    assert by_id.status_code == 200
    payload_by_id = by_id.json()["data"]
    assert payload_by_id["found"] is True
    assert payload_by_id["forecast"]["ticker"] == "AAPL"

    by_ticker = client.get("/forecasts/aapl")
    assert by_ticker.status_code == 200
    payload_by_ticker = by_ticker.json()["data"]
    assert payload_by_ticker["found"] is True
    assert payload_by_ticker["forecast"]["ticker"] == "AAPL"


def test_forecasts_route_fallback_is_explicit_when_service_fails(monkeypatch):
    async def _raise(**_kwargs):
        raise RuntimeError("service exploded")

    monkeypatch.setattr(forecasts_route.forecasts_service, "get_forecasts_payload", _raise)
    client = _client()
    resp = client.get("/forecasts?asset_type=equity&horizon=1w&limit=1")
    assert resp.status_code == 200
    payload = resp.json()["data"]

    assert payload["rows"] == []
    assert "critical_route_error_fallback" in (payload.get("source") or [])
    assert payload.get("fallback_used") is True
    assert "route_exception_fallback" in (payload.get("provider_chain") or [])
    obs = payload.get("observability") or {}
    assert obs.get("fallback_used") is True
    assert "route_exception_fallback" in (obs.get("provider_chain") or [])


def test_forecasts_topk_fast_path_matches_full_sort(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    rows = []
    for i in range(2000):
        rows.append(
            {
                "ticker": f"T{i}",
                "asset_type": "equity",
                "horizon": "1w",
                "score": float(i % 101) / 100.0,
                "confidence": float((i * 7) % 101) / 100.0,
                "expected_return": float((i % 31) - 15) / 100.0,
                "risk_level": ["low", "medium", "high", "critical"][i % 4],
                "timestamp": f"2026-02-{(i % 28) + 1:02d}T00:00:00Z",
            }
        )

    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["test_snapshot"],
        "rows": rows,
    }
    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)

    client = _client()
    fast_resp = client.get(
        "/forecasts?asset_type=equity&horizon=1w&sort_by=score&sort_order=desc&limit=50&offset=0"
    )
    assert fast_resp.status_code == 200
    fast_rows = fast_resp.json()["data"]["rows"]

    full_sorted = sorted(rows, key=lambda row: float(row.get("score", 0.0)), reverse=True)[:50]
    expected_tickers = [row["ticker"] for row in full_sorted]
    actual_tickers = [row["ticker"] for row in fast_rows]
    assert actual_tickers == expected_tickers


def test_forecasts_topk_fast_path_preserves_stable_tie_order(monkeypatch):
    forecasts_route._FORECASTS_RESPONSE_CACHE.clear()
    forecasts_route._FORECASTS_INFLIGHT.clear()

    rows = [
        {"ticker": "AAA", "asset_type": "equity", "horizon": "1w", "score": 0.9, "confidence": 0.5},
        {"ticker": "BBB", "asset_type": "equity", "horizon": "1w", "score": 0.9, "confidence": 0.5},
        {"ticker": "CCC", "asset_type": "equity", "horizon": "1w", "score": 0.9, "confidence": 0.5},
        {"ticker": "DDD", "asset_type": "equity", "horizon": "1w", "score": 0.9, "confidence": 0.5},
        {"ticker": "EEE", "asset_type": "equity", "horizon": "1w", "score": 0.8, "confidence": 0.4},
    ]
    snapshot = {
        "generated_at": "2026-02-27T00:00:00Z",
        "last_update": "2026-02-27T00:00:00Z",
        "source": ["test_snapshot"],
        "rows": rows,
    }
    monkeypatch.setattr(forecasts_route, "load_json", lambda _key: snapshot)

    client = _client()
    fast_resp = client.get(
        "/forecasts?asset_type=equity&horizon=1w&sort_by=score&sort_order=desc&limit=3&offset=0"
    )
    assert fast_resp.status_code == 200
    fast_rows = fast_resp.json()["data"]["rows"]

    full_sorted = sorted(rows, key=lambda row: float(row.get("score", 0.0)), reverse=True)[:3]
    assert [row["ticker"] for row in fast_rows] == [row["ticker"] for row in full_sorted]
