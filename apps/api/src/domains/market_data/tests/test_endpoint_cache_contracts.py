import asyncio
import importlib
import os

os.environ["TEST_ENV"] = "1"
os.environ["SENTRY_DSN"] = ""
os.environ["FRONTEND_SENTRY_DSN"] = ""

from api.services import news_service as news_service_module
from api.main import create_app
from storage import io as storage_io


def _route_endpoint(path: str):
    app = create_app()
    route = next(route for route in app.routes if getattr(route, "path", None) == path)
    return route.endpoint


def test_stocks_prices_contract_and_cache_hit(monkeypatch):
    platform_main = importlib.import_module("platform.main")
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
    monkeypatch.setattr(platform_main, "_STOCKS_PRICES_RESPONSE_CACHE", {})
    endpoint = _route_endpoint("/api/stocks/prices")

    payload_1 = asyncio.run(
        endpoint(ticker="AAPL", tickers=None, timeframe="1y", interval="1d", downsample=200)
    )
    assert payload_1.get("ok") is True
    data_1 = payload_1.get("data") or {}

    assert data_1.get("ticker") == "AAPL"
    assert isinstance(data_1.get("points"), list)
    assert isinstance(data_1.get("stats"), dict)
    assert isinstance(data_1.get("filters_applied"), dict)
    assert "generated_at" in data_1
    assert "source" in data_1

    payload_2 = asyncio.run(
        endpoint(ticker="AAPL", tickers=None, timeframe="1y", interval="1d", downsample=200)
    )
    assert payload_2.get("ok") is True
    data_2 = payload_2.get("data") or {}
    cache_meta = data_2.get("cache") or {}

    assert isinstance(cache_meta, dict)
    assert cache_meta.get("hit") is True
    assert "stocks_prices_cache_hit" in (data_2.get("source") or [])


def test_news_feed_contract_and_cache_hit(monkeypatch):
    platform_main = importlib.import_module("platform.main")
    platform_news_service = importlib.import_module("platform.services.news_service")

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
    monkeypatch.setattr(platform_news_service, "get_news_feed", fake_get_news_feed)
    monkeypatch.setattr(storage_io, "load_json", fake_load_json)
    monkeypatch.setattr(platform_main, "_NEWS_FEED_RESPONSE_CACHE", {})
    endpoint = _route_endpoint("/api/news/feed")

    payload_1 = asyncio.run(
        endpoint(tickers=["AAPL"], since="7d", region="all", score_min=0.0, limit=5)
    )
    assert payload_1.get("ok") is True
    data_1 = payload_1.get("data") or {}

    assert isinstance(data_1.get("items"), list)
    assert isinstance(data_1.get("articles"), list)
    assert isinstance(data_1.get("stats"), dict)
    assert isinstance(data_1.get("filters_applied"), dict)
    assert "generated_at" in data_1
    assert "source" in data_1

    payload_2 = asyncio.run(
        endpoint(tickers=["AAPL"], since="7d", region="all", score_min=0.0, limit=5)
    )
    assert payload_2.get("ok") is True
    data_2 = payload_2.get("data") or {}
    cache_meta = data_2.get("cache") or {}

    assert isinstance(cache_meta, dict)
    assert cache_meta.get("hit") is True
    assert "news_feed_cache_hit" in (data_2.get("source") or [])


def test_copilot_context_fallback_keeps_copilot_start_contract(monkeypatch):
    platform_main = importlib.import_module("platform.main")

    def fake_market_context_snapshot():
        raise RuntimeError("context unavailable")

    def fake_copilot_start_payload(*, context_timestamp=None):
        return {
            "brief_of_day": {
                "title": "Brief of the day",
                "summary": "No daily brief available yet.",
                "market_sentiment": "UNKNOWN",
                "top_signals": [],
                "top_risks": [],
                "macro_signals": [],
                "sector_rotation": {"top": [], "bottom": []},
                "generated_at": context_timestamp,
                "freshness": context_timestamp,
                "source": ["brief_daily_fallback"],
            },
            "ask": [
                {
                    "id": "portfolio_today",
                    "label": "Portfolio today?",
                    "prompt": "What should I do with my portfolio today?",
                }
            ],
            "open": [
                {
                    "id": "market",
                    "label": "Open market view",
                    "target": "market",
                }
            ],
        }

    monkeypatch.setattr(platform_main, "get_market_context_snapshot", fake_market_context_snapshot)
    monkeypatch.setattr(platform_main, "build_copilot_start_payload", fake_copilot_start_payload)

    endpoint = _route_endpoint("/api/copilot/context")
    payload = asyncio.run(endpoint())

    assert payload.get("ok") is True
    data = payload.get("data") or {}
    copilot_start = data.get("copilot_start") or {}
    brief_of_day = copilot_start.get("brief_of_day") or {}

    assert data.get("note") == "Market context service temporarily unavailable."
    assert brief_of_day.get("summary") == "No daily brief available yet."
    assert brief_of_day.get("source") == ["brief_daily_fallback"]
    assert copilot_start.get("ask", [])[0]["id"] == "portfolio_today"
    assert copilot_start.get("open", [])[0]["target"] == "market"
