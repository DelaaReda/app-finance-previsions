"""
BATCH-61-DEV-03: Brief of the Day Feature Test

Tests the minimal vertical slice for the personal finance copilot
that starts with a brief of the day.

Product requirement:
- The copilot must start with a brief of the day
- The brief must include: summary, market_sentiment, top_signals, top_risks
- The brief must be visible in /copilot/start and /copilot/context endpoints
- Freshness and source must be explicit
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domains.copilot.api.copilot import router
from storage import io as storage_io


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_brief_of_day_appears_in_copilot_start_with_required_fields():
    """
    DEV-03: Brief of the day must appear in /copilot/start with required fields.
    
    Required brief fields:
    - summary: short market overview (< 200 words)
    - market_sentiment: BULLISH/BEARISH/UNKNOWN
    - top_signals: list of key positive signals
    - top_risks: list of key risks to watch
    - generated_at: ISO timestamp
    - freshness: ISO timestamp (can be same as generated_at)
    - source: list of source identifiers
    """
    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "Markets open calm with bullish bias on mega caps. Semiconductors lead while rates remain stable.",
                "market_sentiment": "BULLISH",
                "top_signals": [
                    {"name": "NVDA guidance", "value": "beat", "signal": "positive"},
                    {"name": "VIX", "value": "14.2", "signal": "low_volatility"},
                ],
                "top_risks": [
                    {"name": "CPI release", "value": "tomorrow", "signal": "watch"},
                ],
                "macro_signals": [
                    {"name": "DXY", "value": "103.5", "signal": "neutral"},
                ],
                "sector_rotation": {
                    "top": ["Semiconductors", "Tech"],
                    "bottom": ["Utilities", "Staples"],
                },
                "generated_at": "2026-03-09T08:30:00Z",
                "freshness": "2026-03-09T08:30:00Z",
                "source": ["brief_daily_generator", "forecasts_snapshot"],
            }
        }
    }

    def mock_load_json(key):
        return brief_snapshot if key == "brief_daily" else None

    # Patch storage load
    original_load = storage_io.load_json
    storage_io.load_json = mock_load_json

    try:
        client = _client()
        response = client.get("/api/copilot/start")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        payload = response.json()
        assert payload.get("ok") is True, "Response should have ok=True"
        
        data = payload.get("data") or {}
        
        # DEV-03: Brief of day must be present
        brief_of_day = data.get("brief_of_day")
        assert brief_of_day is not None, "brief_of_day must be present in /copilot/start"
        
        # Required fields validation
        assert "summary" in brief_of_day, "brief_of_day must have 'summary' field"
        assert isinstance(brief_of_day["summary"], str), "summary must be a string"
        assert len(brief_of_day["summary"].split()) <= 200, "summary must be < 200 words"
        
        assert "market_sentiment" in brief_of_day, "brief_of_day must have 'market_sentiment' field"
        assert brief_of_day["market_sentiment"] in {"BULLISH", "BEARISH", "UNKNOWN", "NEUTRAL"}, \
            "market_sentiment must be BULLISH/BEARISH/UNKNOWN/NEUTRAL"
        
        assert "top_signals" in brief_of_day, "brief_of_day must have 'top_signals' field"
        assert isinstance(brief_of_day["top_signals"], list), "top_signals must be a list"
        
        assert "top_risks" in brief_of_day, "brief_of_day must have 'top_risks' field"
        assert isinstance(brief_of_day["top_risks"], list), "top_risks must be a list"
        
        assert "generated_at" in brief_of_day, "brief_of_day must have 'generated_at' field"
        assert brief_of_day["generated_at"].endswith("Z"), "generated_at must be ISO format with Z"
        
        assert "freshness" in brief_of_day, "brief_of_day must have 'freshness' field"
        assert brief_of_day["freshness"].endswith("Z"), "freshness must be ISO format with Z"
        
        assert "source" in brief_of_day, "brief_of_day must have 'source' field"
        assert isinstance(brief_of_day["source"], list), "source must be a list"
        assert len(brief_of_day["source"]) > 0, "source must have at least one entry"
        
        # Verify the test brief content
        assert "bullish" in brief_of_day["summary"].lower() or "bullish" == brief_of_day["market_sentiment"].lower()
        assert "brief_daily_generator" in brief_of_day["source"]
        assert "forecasts_snapshot" in brief_of_day["source"]
        
    finally:
        storage_io.load_json = original_load


def test_brief_of_day_fallback_when_no_snapshot_available():
    """
    DEV-03: When no brief snapshot exists, a fallback brief must be provided.
    
    The fallback must still satisfy the contract:
    - summary (fallback message)
    - market_sentiment (UNKNOWN)
    - top_signals (empty list)
    - top_risks (empty list)
    - generated_at (current time)
    - freshness (current time)
    - source (fallback identifier)
    """
    def mock_load_json_empty(key):
        return None

    original_load = storage_io.load_json
    storage_io.load_json = mock_load_json_empty

    try:
        client = _client()
        response = client.get("/api/copilot/start")
        
        assert response.status_code == 200
        
        payload = response.json()
        data = payload.get("data") or {}
        brief_of_day = data.get("brief_of_day")
        
        assert brief_of_day is not None, "brief_of_day must always be present (even fallback)"
        assert "summary" in brief_of_day
        assert "market_sentiment" in brief_of_day
        assert brief_of_day["market_sentiment"] == "UNKNOWN"
        assert "top_signals" in brief_of_day
        assert isinstance(brief_of_day["top_signals"], list)
        assert "top_risks" in brief_of_day
        assert isinstance(brief_of_day["top_risks"], list)
        assert "generated_at" in brief_of_day
        assert "freshness" in brief_of_day
        assert "source" in brief_of_day
        assert "fallback" in str(brief_of_day["source"]).lower()
        
    finally:
        storage_io.load_json = original_load


def test_brief_of_day_in_context_endpoint():
    """
    DEV-03: Brief of day must also appear in /copilot/context endpoint.
    """
    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "Tech leads with AI momentum continuing.",
                "market_sentiment": "BULLISH",
                "top_signals": [{"name": "AI demand", "value": "strong"}],
                "top_risks": [],
                "generated_at": "2026-03-09T09:00:00Z",
                "freshness": "2026-03-09T09:00:00Z",
                "source": ["test_context"],
            }
        }
    }

    def mock_load_json(key):
        return brief_snapshot if key == "brief_daily" else None

    original_load = storage_io.load_json
    storage_io.load_json = mock_load_json

    try:
        client = _client()
        response = client.get("/api/copilot/context")
        
        assert response.status_code == 200
        
        payload = response.json()
        data = payload.get("data") or {}
        
        # Brief in context
        daily_brief = data.get("daily_brief")
        assert daily_brief is not None, "daily_brief must be present in /copilot/context"
        assert "Tech leads with AI momentum continuing." in daily_brief["summary"]
        assert daily_brief["market_sentiment"] == "BULLISH"
        
        # Brief also in copilot_start within context
        copilot_start = data.get("copilot_start") or {}
        brief_in_start = copilot_start.get("brief_of_day")
        assert brief_in_start is not None, "brief_of_day must be in copilot_start within context"
        assert brief_in_start["summary"] == daily_brief["summary"]
        
    finally:
        storage_io.load_json = original_load


def test_brief_of_day_with_ticker_scope():
    """
    DEV-03: Brief of day should work with ticker scope.
    """
    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "NVDA leads semiconductor rally.",
                "market_sentiment": "BULLISH",
                "top_signals": [{"name": "NVDA", "value": "+5%", "signal": "positive"}],
                "top_risks": [],
                "generated_at": "2026-03-09T10:00:00Z",
                "freshness": "2026-03-09T10:00:00Z",
                "source": ["scoped_brief"],
            }
        }
    }

    def mock_load_json(key):
        return brief_snapshot if key == "brief_daily" else None

    original_load = storage_io.load_json
    storage_io.load_json = mock_load_json

    try:
        client = _client()
        response = client.get("/api/copilot/start?tickers=nvda&tickers=msft")
        
        assert response.status_code == 200
        
        payload = response.json()
        data = payload.get("data") or {}
        
        # Scope tickers applied
        assert data.get("scope_tickers") == ["MSFT", "NVDA"]
        assert data.get("filters_applied", {}).get("tickers") == ["MSFT", "NVDA"]
        
        # Brief still present
        brief_of_day = data.get("brief_of_day")
        assert brief_of_day is not None
        assert "NVDA" in brief_of_day["summary"]
        
    finally:
        storage_io.load_json = original_load
