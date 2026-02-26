from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from src.api import main as api_main
from src.api.main import create_app
from storage import io as storage_io


def _client() -> TestClient:
    return TestClient(create_app())


def test_stocks_prices_multi_ticker_comma_separated_contract(monkeypatch):
    snapshot = {
        "freshness": "2026-02-26T00:00:00Z",
        "tickers": {
            "AAPL": {
                "range": "1y",
                "interval": "1d",
                "points": [[1700000000, 150.0], [1700086400, 151.5]],
                "start_date": "2025-02-26",
            },
            "MSFT": {
                "range": "1y",
                "interval": "1d",
                "points": [[1700000000, 300.0], [1700086400, 301.1]],
                "start_date": "2025-02-26",
            },
        },
    }

    def fake_load_json(key):
        if key in {"stocks/prices", "stocks/prices.json"}:
            return snapshot
        return {}

    monkeypatch.setattr(storage_io, "load_json", fake_load_json)
    monkeypatch.setattr(api_main, "_STOCKS_PRICES_RESPONSE_CACHE", {})

    client = _client()
    response = client.get(
        "/api/stocks/prices?tickers=AAPL,MSFT&timeframe=1y&interval=1d&downsample=200"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert isinstance(data.get("tickers"), dict)
    assert sorted(data["tickers"].keys()) == ["AAPL", "MSFT"]
    assert sorted(data.get("filters_applied", {}).get("resolved_tickers", [])) == [
        "AAPL",
        "MSFT",
    ]
    assert data.get("stats", {}).get("requested_tickers") == 2
    for symbol in ("AAPL", "MSFT"):
        entry = data["tickers"][symbol]
        assert isinstance(entry.get("points"), list)
        assert "count" in entry
        assert "timestamp" in entry


def test_stocks_prices_missing_ticker_never_500(monkeypatch):
    def fake_load_json(key):
        if key in {"stocks/prices", "stocks/prices.json"}:
            return {"freshness": "2026-02-26T00:00:00Z", "tickers": {}}
        return {}

    def fake_get_price_history(_ticker, **_kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(storage_io, "load_json", fake_load_json)
    monkeypatch.setattr(api_main, "get_price_history", fake_get_price_history)
    monkeypatch.setattr(api_main, "_STOCKS_PRICES_RESPONSE_CACHE", {})

    client = _client()
    response = client.get("/api/stocks/prices?timeframe=1y&interval=1d&downsample=200")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("ok") is True
    data = payload.get("data") or {}

    assert isinstance(data.get("tickers"), dict)
    assert len(data.get("filters_applied", {}).get("resolved_tickers", [])) >= 1
    assert data.get("stats", {}).get("requested_tickers", 0) >= 1
    assert "source" in data
