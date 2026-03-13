from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict


SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

ALERTS_JOB_PATH = SRC_ROOT / "platform" / "legacy" / "jobs" / "alerts.py"
SPEC = importlib.util.spec_from_file_location("alerts_job_contract_test", ALERTS_JOB_PATH)
assert SPEC is not None and SPEC.loader is not None
ALERTS_JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ALERTS_JOB)


def test_compute_alerts_returns_deterministic_deduped_contract(monkeypatch):
    def fake_load_json(name: str) -> Dict[str, Any]:
        if name == "forecasts":
            return {
                "payload": {
                    "rows": [
                        {"ticker": "AAPL", "direction": "down", "confidence": 0.74},
                        {"ticker": "AAPL", "direction": "down", "confidence": 0.88},
                        {"ticker": "MSFT", "direction": "up", "confidence": 0.61},
                        {"ticker": "MSFT", "direction": "up", "confidence": 79},
                    ]
                }
            }
        if name == "news_feed":
            return {
                "payload": {
                    "articles": [
                        {
                            "tickers": ["AAPL"],
                            "sentiment_score": -0.65,
                            "title": "AAPL update",
                            "pubDate": "2026-03-04T06:10:00Z",
                        },
                        {
                            "tickers": ["MSFT"],
                            "sentiment_score": 0.92,
                            "title": "MSFT update",
                            "pubDate": "2026-03-04T06:12:00Z",
                        },
                    ]
                }
            }
        if name == "alerts":
            return {}
        return {}

    def fake_seeded_float(seed: str) -> float:
        if seed.startswith("alerts:rsi:AAPL:2026030406"):
            return 0.05  # force oversold
        if seed.startswith("alerts:rsi:MSFT:2026030406"):
            return 0.95  # force overbought
        if seed.startswith("alerts:vol:"):
            return 0.55  # deterministic high volatility
        return 0.5

    monkeypatch.setattr(ALERTS_JOB, "load_json", fake_load_json)
    monkeypatch.setattr(ALERTS_JOB, "_seeded_float", fake_seeded_float)

    run_at = datetime(2026, 3, 4, 6, 20, 0, tzinfo=timezone.utc)
    first = ALERTS_JOB.compute_alerts(now=run_at)
    second = ALERTS_JOB.compute_alerts(now=run_at)

    assert first["generated_at"] == second["generated_at"]
    assert isinstance(first.get("alerts"), list)
    assert first.get("count") == len(first["alerts"]) == first["stats"]["generated"]
    assert first["stats"]["scanned_tickers"] == 10

    signatures = {(item.get("ticker"), item.get("type"), item.get("summary", "")) for item in first["alerts"]}
    assert len(signatures) == len(first["alerts"])  # no duplicates by signature

    for alert in first["alerts"]:
        assert 0.0 <= alert["confidence"] <= 1.0
        assert alert["severity"] in {"critical", "high", "warning", "medium", "low", "info"}
        assert alert["priority_score"] >= 0
        assert alert["priority_band"] in {"urgent", "high", "medium", "low"}
        assert alert["priority_rank"] >= 1
        assert alert["suppression"]["suppressed"] is False

    assert first["pipeline"]["priority_ordering"] is True
    assert first["pipeline"]["suppression_window_minutes"] == 15
    assert first["stats"]["candidate_alerts"] >= first["count"]


def test_compute_alerts_suppresses_fatigue_duplicates_within_window(monkeypatch):
    run_at = datetime(2026, 3, 4, 6, 20, 0, tzinfo=timezone.utc)

    def fake_load_json(name: str) -> Dict[str, Any]:
        if name == "forecasts":
            return {
                "payload": {
                    "rows": [
                        {"ticker": "AAPL", "direction": "down", "confidence": 0.74},
                        {"ticker": "AAPL", "direction": "down", "confidence": 0.88},
                    ]
                }
            }
        if name == "news_feed":
            return {
                "payload": {
                    "articles": [
                        {
                            "tickers": ["AAPL"],
                            "sentiment_score": -0.65,
                            "title": "AAPL update",
                            "pubDate": "2026-03-04T06:10:00Z",
                        },
                    ]
                }
            }
        if name == "alerts":
            return {
                "alerts": [
                    {
                        "ticker": "AAPL",
                        "type": "oversold-bearish",
                        "summary": "oversold-bearish:AAPL:down",
                        "severity": "medium",
                        "confidence": 0.95,
                        "timestamp": "2026-03-04T06:08:00Z",
                        "signature": "AAPL|oversold-bearish|oversold-bearish:AAPL:down|0.950|medium",
                        "suppression": {"repeat_count": 2},
                    }
                ]
            }
        return {}

    def fake_seeded_float(seed: str) -> float:
        if seed.startswith("alerts:rsi:AAPL:2026030406"):
            return 0.05
        return 0.5

    monkeypatch.setattr(ALERTS_JOB, "load_json", fake_load_json)
    monkeypatch.setattr(ALERTS_JOB, "_seeded_float", fake_seeded_float)

    payload = ALERTS_JOB.compute_alerts(now=run_at)

    assert payload["alerts"] == []
    assert payload["count"] == 0
    assert payload["suppressed_count"] == 1
    assert payload["stats"]["suppressed_duplicates"] == 1
    assert payload["warnings"] == ["duplicate_alerts_suppressed"]
    suppressed = payload["suppressed_alerts"][0]
    assert suppressed["suppression"]["suppressed"] is True
    assert suppressed["suppression"]["reason"] == "fatigue_window_duplicate"
    assert suppressed["suppression"]["repeat_count"] == 3


def test_compute_alerts_keeps_escalated_duplicate_visible_within_window(monkeypatch):
    run_at = datetime(2026, 3, 4, 6, 20, 0, tzinfo=timezone.utc)

    def fake_load_json(name: str) -> Dict[str, Any]:
        if name == "forecasts":
            return {
                "payload": {
                    "rows": [
                        {"ticker": "AAPL", "direction": "up", "confidence": 0.82},
                    ]
                }
            }
        if name == "news_feed":
            return {
                "payload": {
                    "articles": [
                        {
                            "tickers": ["AAPL"],
                            "sentiment_score": 0.88,
                            "title": "AAPL update",
                            "pubDate": "2026-03-04T06:12:00Z",
                        },
                        {
                            "tickers": ["AAPL"],
                            "sentiment_score": 0.91,
                            "title": "AAPL follow-up",
                            "pubDate": "2026-03-04T06:16:00Z",
                        },
                    ]
                }
            }
        if name == "alerts":
            return {
                "alerts": [
                    {
                        "ticker": "AAPL",
                        "type": "breakout-news",
                        "summary": "breakout-news:AAPL:2",
                        "severity": "medium",
                        "confidence": 0.62,
                        "timestamp": "2026-03-04T06:12:00Z",
                        "signature": "AAPL|breakout-news|breakout-news:AAPL:2|0.620|medium",
                        "suppression": {"repeat_count": 2},
                    }
                ]
            }
        return {}

    def fake_seeded_float(seed: str) -> float:
        if seed.startswith("alerts:vol:AAPL:202603040620"):
            return 0.95
        return 0.5

    monkeypatch.setattr(ALERTS_JOB, "load_json", fake_load_json)
    monkeypatch.setattr(ALERTS_JOB, "_seeded_float", fake_seeded_float)

    payload = ALERTS_JOB.compute_alerts(now=run_at)

    assert payload["count"] == 1
    assert payload["suppressed_count"] == 0
    alert = payload["alerts"][0]
    assert alert["type"] == "breakout-news"
    assert alert["severity"] == "high"
    assert alert["priority_band"] in {"urgent", "high"}
    assert alert["suppression"]["suppressed"] is False
    assert alert["suppression"]["repeat_count"] == 3


def test_compute_alerts_reuses_suppressed_snapshot_state(monkeypatch):
    run_at = datetime(2026, 3, 4, 6, 20, 0, tzinfo=timezone.utc)

    def fake_load_json(name: str) -> Dict[str, Any]:
        if name == "forecasts":
            return {
                "payload": {
                    "rows": [
                        {"ticker": "AAPL", "direction": "down", "confidence": 0.74},
                    ]
                }
            }
        if name == "news_feed":
            return {
                "payload": {
                    "articles": [
                        {
                            "tickers": ["AAPL"],
                            "sentiment_score": -0.65,
                            "title": "AAPL update",
                            "pubDate": "2026-03-04T06:10:00Z",
                        },
                    ]
                }
            }
        if name == "alerts":
            return {
                "alerts": [],
                "suppressed_alerts": [
                    {
                        "ticker": "AAPL",
                        "type": "oversold-bearish",
                        "summary": "oversold-bearish:AAPL:down",
                        "severity": "medium",
                        "confidence": 0.84,
                        "timestamp": "2026-03-04T06:10:00Z",
                        "signature": "AAPL|oversold-bearish|oversold-bearish:AAPL:down|0.840|medium",
                        "suppression": {"repeat_count": 3},
                    }
                ],
            }
        return {}

    def fake_seeded_float(seed: str) -> float:
        if seed.startswith("alerts:rsi:AAPL:2026030406"):
            return 0.05
        return 0.5

    monkeypatch.setattr(ALERTS_JOB, "load_json", fake_load_json)
    monkeypatch.setattr(ALERTS_JOB, "_seeded_float", fake_seeded_float)

    payload = ALERTS_JOB.compute_alerts(now=run_at)

    assert payload["alerts"] == []
    assert payload["count"] == 0
    assert payload["suppressed_count"] == 1
    suppressed = payload["suppressed_alerts"][0]
    assert suppressed["suppression"]["suppressed"] is True
    assert suppressed["suppression"]["reason"] == "fatigue_window_duplicate"
    assert suppressed["suppression"]["repeat_count"] == 4


def test_compute_alerts_handles_sparse_direction_forecasts_without_crashing(monkeypatch):
    run_at = datetime(2026, 3, 4, 6, 20, 0, tzinfo=timezone.utc)

    def fake_load_json(name: str) -> Dict[str, Any]:
        if name == "forecasts":
            return {
                "payload": {
                    "rows": [
                        {"ticker": "AAPL", "direction": "down", "confidence": 0.74},
                    ]
                }
            }
        if name == "news_feed":
            return {
                "payload": {
                    "articles": [
                        {
                            "tickers": ["AAPL"],
                            "sentiment_score": -0.65,
                            "title": "AAPL update",
                            "pubDate": "2026-03-04T06:10:00Z",
                        },
                        {
                            "tickers": ["MSFT"],
                            "sentiment_score": 0.92,
                            "title": "MSFT update",
                            "pubDate": "2026-03-04T06:12:00Z",
                        },
                    ]
                }
            }
        if name == "alerts":
            return {}
        return {}

    def fake_seeded_float(seed: str) -> float:
        if seed.startswith("alerts:rsi:AAPL:2026030406"):
            return 0.05
        if seed.startswith("alerts:rsi:MSFT:2026030406"):
            return 0.95
        if seed.startswith("alerts:vol:"):
            return 0.1
        return 0.5

    monkeypatch.setattr(ALERTS_JOB, "load_json", fake_load_json)
    monkeypatch.setattr(ALERTS_JOB, "_seeded_float", fake_seeded_float)

    payload = ALERTS_JOB.compute_alerts(now=run_at)

    assert payload["count"] == 1
    assert payload["alerts"][0]["ticker"] == "AAPL"
    assert payload["alerts"][0]["type"] == "oversold-bearish"
    assert payload["suppressed_count"] == 0
