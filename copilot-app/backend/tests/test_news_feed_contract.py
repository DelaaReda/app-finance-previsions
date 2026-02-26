from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import main as api_main
from src.api.main import create_app
from src.api.services import news_service as news_service_module
from storage import io as storage_io


def _client() -> TestClient:
    return TestClient(create_app())


def test_news_feed_normalized_items_and_resolved_tickers(monkeypatch):
    async def fake_get_news_feed(*args, **kwargs):
        return {
            "ok": True,
            "data": {
                "items": [
                    {
                        "title": "Apple earnings beat",
                        "url": "https://example.com/aapl",
                        "published_at": "2026-02-25T09:00:00Z",
                        "source": "ExampleWire",
                        "tickers": ["AAPL"],
                        "score": 0.9,
                    },
                    {
                        "headline": "Microsoft guidance raised",
                        "link": "https://example.com/msft",
                        "date": "2026-02-25T08:00:00Z",
                        "ticker": "MSFT",
                        "score": "0.42",
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
    response = client.get("/api/news/feed?tickers=AAPL,MSFT&since=30d&score_min=0.0&limit=10")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("ok") is True
    data = payload.get("data") or {}

    items = data.get("items") or []
    assert isinstance(items, list)
    assert len(items) == 2
    assert data.get("count") == len(items)
    assert data.get("articles") == items
    assert sorted(data.get("filters_applied", {}).get("resolved_tickers", [])) == [
        "AAPL",
        "MSFT",
    ]

    for item in items:
        assert "title" in item
        assert "url" in item
        assert "source" in item
        assert "date" in item
        assert "published_at" in item
        assert "tickers" in item
        assert "score" in item
        assert isinstance(item["source"], str)
        assert item["source"].strip() != ""
