"""
BATCH-24-DEV-03: Market brief alerting contract regression test.

Verifies the brief job reuses the shared alerting defaults instead of
hard-coding suppression metadata on the active brief path.
"""
import sys
from pathlib import Path

import pytest


SRC_PATH = str(Path(__file__).parent.parent.parent)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from platform.legacy.jobs import market_brief
from storage import base as storage_base


def test_market_brief_reuses_shared_alerting_defaults(monkeypatch):
    monkeypatch.setattr(
        market_brief,
        "get_alerting_contract_defaults",
        lambda: {
            "suppression_window_minutes": 30,
            "fatigue_threshold": 4,
            "duplicate_suppression_reason": "fatigue_window_duplicate",
            "urgent_bypass_enabled": False,
        },
    )
    monkeypatch.setattr(
        storage_base,
        "load_forecasts",
        lambda: {
            "data": {
                "rows": [
                    {
                        "ticker": "AAPL",
                        "direction": "down",
                        "confidence": 0.72,
                        "expected_return": -0.02,
                        "horizon": "1d",
                        "sector": "technology",
                        "reasoning": "Momentum is fading.",
                        "model": "forecasts",
                    },
                    {
                        "ticker": "AAPL",
                        "direction": "down",
                        "confidence": 0.68,
                        "expected_return": -0.015,
                        "horizon": "1d",
                        "sector": "technology",
                        "reasoning": "Duplicate bearish read.",
                        "model": "forecasts",
                    },
                ]
            }
        },
    )
    monkeypatch.setattr(storage_base, "load_news_feed", lambda: {"data": {"articles": []}})
    monkeypatch.setattr(storage_base, "load_json", lambda _key: {"data": {}})

    captured = {}

    def fake_save_json(payload, path, **_kwargs):
        captured["payload"] = payload
        captured["path"] = path

    monkeypatch.setattr(storage_base, "save_json", fake_save_json)

    result = market_brief.run_market_brief_job()

    assert result["brief_generated"] is True
    brief = result["brief_data"]
    assert captured["path"] == "brief_daily.json"
    assert brief["top_risks"][0]["suppression_window_minutes"] == 30
    assert brief["suppressed_risks"][0]["suppression_reason"] == "fatigue_window_duplicate"
    assert brief["alerting_metadata"]["suppression_window_minutes"] == 30
    assert brief["alerting_metadata"]["fatigue_threshold"] == 4
    assert brief["alerting_metadata"]["urgent_bypass_enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
