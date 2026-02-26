from fastapi.testclient import TestClient

from src.api import main as api_main
from src.api.services import news_service as news_service_module
from src.api.main import create_app
from storage import io as storage_io


def _client() -> TestClient:
    return TestClient(create_app())


def test_stocks_prices_contract_and_cache_hit(monkeypatch):
    snapshot = {
        "freshness": "2026-02-25T10:00:00Z",
        "tickers": {
            "AAPL": {
                "range": "1y",
                "interval": "1d",
                "points": [[1700000000, 150.0], [1700086400, 151.5], [1700172800, 153.2]],
                "start_date": "2025-02-25",
            }
        },
    }

    def fake_load_json(key):
        if key in {"stocks/prices", "stocks/prices.json"}:
            return snapshot
        return {}

    monkeypatch.setattr(storage_io, "load_json", fake_load_json)
    monkeypatch.setattr(api_main, "_STOCKS_PRICES_RESPONSE_CACHE", {})
    client = _client()
    path = "/api/stocks/prices?ticker=AAPL&timeframe=1y&interval=1d&downsample=200"

    first = client.get(path)
    assert first.status_code == 200
    payload_1 = first.json()
    assert payload_1.get("ok") is True
    data_1 = payload_1.get("data") or {}

    assert data_1.get("ticker") == "AAPL"
    assert isinstance(data_1.get("points"), list)
    assert isinstance(data_1.get("stats"), dict)
    assert isinstance(data_1.get("filters_applied"), dict)
    assert "generated_at" in data_1
    assert "source" in data_1

    second = client.get(path)
    assert second.status_code == 200
    payload_2 = second.json()
    assert payload_2.get("ok") is True
    data_2 = payload_2.get("data") or {}
    cache_meta = data_2.get("cache") or {}

    assert isinstance(cache_meta, dict)
    assert cache_meta.get("hit") is True
    assert "stocks_prices_cache_hit" in (data_2.get("source") or [])


def test_news_feed_contract_and_cache_hit(monkeypatch):
    async def fake_get_news_feed(*args, **kwargs):
        return {
            "ok": True,
            "data": {
                "items": [
                    {
                        "title": "Apple quarterly results",
                        "url": "https://example.com/aapl-q",
                        "published_at": "2026-02-25T09:00:00Z",
                        "source": "ExampleWire",
                        "tickers": ["AAPL"],
                        "score": 0.81,
                    },
                    {
                        "title": "Apple guidance update",
                        "url": "https://example.com/aapl-guidance",
                        "published_at": "2026-02-25T08:00:00Z",
                        "source": "ExampleWire",
                        "tickers": ["AAPL"],
                        "score": 0.72,
                    },
                ],
                "generated_at": "2026-02-25T09:05:00Z",
                "source": ["fake_news_service"],
            },
        }

    def fake_load_json(_key):
        return {}

    monkeypatch.setattr(news_service_module, "get_news_feed", fake_get_news_feed)
    monkeypatch.setattr(storage_io, "load_json", fake_load_json)
    monkeypatch.setattr(api_main, "_NEWS_FEED_RESPONSE_CACHE", {})

    client = _client()
    path = "/api/news/feed?tickers=AAPL&since=7d&score_min=0.0&limit=5"

    first = client.get(path)
    assert first.status_code == 200
    payload_1 = first.json()
    assert payload_1.get("ok") is True
    data_1 = payload_1.get("data") or {}

    assert isinstance(data_1.get("items"), list)
    assert isinstance(data_1.get("articles"), list)
    assert isinstance(data_1.get("stats"), dict)
    assert isinstance(data_1.get("filters_applied"), dict)
    assert "generated_at" in data_1
    assert "source" in data_1

    second = client.get(path)
    assert second.status_code == 200
    payload_2 = second.json()
    assert payload_2.get("ok") is True
    data_2 = payload_2.get("data") or {}
    cache_meta = data_2.get("cache") or {}

    assert isinstance(cache_meta, dict)
    assert cache_meta.get("hit") is True
    assert "news_feed_cache_hit" in (data_2.get("source") or [])
