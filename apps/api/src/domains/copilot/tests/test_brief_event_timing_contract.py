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


def test_copilot_start_derives_event_timing_from_brief_key_events():
    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "Rates stay range-bound while event density rises.",
                "market_regime": "NEUTRAL",
                "market_sentiment": "NEUTRAL",
                "top_opportunities": [],
                "top_signals": [],
                "top_risks": ["Headline volatility"],
                "key_events": [
                    {
                        "label": "NVDA earnings",
                        "window": "24h",
                        "summary": "Guidance risk is concentrated in the next session.",
                    },
                    {
                        "label": "CPI release",
                        "window": "48h",
                        "summary": "Rates could reset quickly after the print.",
                    },
                ],
                "generated_at": "2026-03-09T09:00:00Z",
                "freshness": "2026-03-09T09:00:00Z",
                "sources": ["brief_daily_generator"],
                "source": ["brief_daily_generator"],
            }
        }
    }

    def mock_load_json(key):
        return brief_snapshot if key == "brief_daily" else None

    original_load = storage_io.load_json
    storage_io.load_json = mock_load_json

    try:
        client = _client()
        response = client.get("/api/copilot/start")

        assert response.status_code == 200
        brief_of_day = (response.json().get("data") or {}).get("brief_of_day") or {}
        event_timing = brief_of_day.get("event_timing") or {}

        assert event_timing["summary"] == "Critical events are clustered into the next 48h."
        assert event_timing["freshness"] == "2026-03-09T09:00:00Z"
        assert event_timing["source"] == ["brief_daily_generator"]
        assert event_timing["events"] == [
            {
                "event_type": "NVDA earnings",
                "dominant_horizon": "24h",
                "interpretation": "Guidance risk is concentrated in the next session.",
            },
            {
                "event_type": "CPI release",
                "dominant_horizon": "48h",
                "interpretation": "Rates could reset quickly after the print.",
            },
        ]
    finally:
        storage_io.load_json = original_load
