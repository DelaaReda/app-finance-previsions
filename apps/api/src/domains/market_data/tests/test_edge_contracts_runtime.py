from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import importlib.util

PLATFORM_MAIN_PATH = SRC_ROOT / "platform" / "main.py"


def _load_platform_main():
    spec = importlib.util.spec_from_file_location("fc_platform_main_test", PLATFORM_MAIN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_client(monkeypatch):
    platform_main = _load_platform_main()
    monkeypatch.setenv("FC_API_EDGE_FORECASTS", "1")
    monkeypatch.setenv("FC_API_EDGE_RECOMMENDATIONS", "1")
    monkeypatch.setenv("FC_API_EDGE_STOCKS", "1")

    # Keep tests deterministic and local-only.
    monkeypatch.setattr(platform_main, "get_close_series", lambda _ticker: None)
    monkeypatch.setattr(
        platform_main,
        "get_price_history",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )
    monkeypatch.setattr(platform_main, "get_fundamentals", lambda *_args, **_kwargs: {})

    app = platform_main.create_app()
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    return TestClient(app)


def _assert_edge_shape(payload: dict):
    assert isinstance(payload, dict)
    assert "ok" in payload
    assert "data" in payload
    assert payload.get("status") in {"ok", "degraded", "error"}
    assert "meta" in payload and isinstance(payload.get("meta"), dict)
    meta = payload["meta"]
    for key in ("source", "request_id", "schema_version", "fallback"):
        assert key in meta


def test_forecasts_endpoint_exposes_edge_contract(monkeypatch):
    client = _build_client(monkeypatch)
    resp = client.get("/api/forecasts?horizon=short&limit=2")
    assert resp.status_code == 200
    payload = resp.json()
    _assert_edge_shape(payload)


def test_recommendations_endpoint_exposes_edge_contract(monkeypatch):
    client = _build_client(monkeypatch)
    resp = client.get("/api/recommendations/daily?limit=3")
    assert resp.status_code == 200
    payload = resp.json()
    _assert_edge_shape(payload)
    assert isinstance(payload.get("data"), dict)
    assert "recommendations" in payload["data"]


def test_stocks_sheet_returns_degraded_contract_instead_of_raw_404(monkeypatch):
    client = _build_client(monkeypatch)
    resp = client.get("/api/stocks/UNKNOWN/sheet")
    assert resp.status_code == 200
    payload = resp.json()
    _assert_edge_shape(payload)
    assert payload.get("status") == "degraded"
    assert isinstance(payload.get("error"), dict)
    assert payload["error"].get("code")
