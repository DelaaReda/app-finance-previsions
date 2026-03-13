from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


API_SRC = Path(__file__).resolve().parents[3]
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

MODULE_PATH = Path(__file__).resolve().parents[1] / "application" / "intelligence_service.py"
SPEC = importlib.util.spec_from_file_location("fc_intelligence_service_cache_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["fc_intelligence_service_cache_test"] = MODULE
SPEC.loader.exec_module(MODULE)


class IntelligenceServiceCacheTests(unittest.TestCase):
    def test_market_context_cache_is_backfilled_and_refreshed_when_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            old_cache = tmp / "market_context_snapshot.json"
            old_cache.write_text(
                (
                    "{"
                    '"regime":"BEAR_MARKET",'
                    '"confidence":0.37,'
                    '"key_drivers":[],'
                    '"characteristics":{"volatility":"extreme"},'
                    '"recommended_layout":{"primary_widgets":["intelligence"]},'
                    '"timestamp":"2026-02-28T21:05:36.647901+00:00"'
                    "}"
                ),
                encoding="utf-8",
            )

            with mock.patch.object(MODULE, "CACHE_FILE_CONTEXT", old_cache), mock.patch.object(
                MODULE, "_load_forecasts", return_value=[{"ticker": "AAPL", "expected_return": 0.01}]
            ), mock.patch.object(MODULE, "_load_news", return_value=[]), mock.patch.object(
                MODULE, "_load_brief", return_value={}
            ):
                payload = MODULE.get_market_context_snapshot(use_cache=True, persist=True)

            metadata = payload.get("metadata") or {}
            self.assertIsInstance(metadata, dict)
            self.assertTrue(metadata.get("generated_at"))
            self.assertEqual(metadata.get("sources"), ["intelligence", "forecasts", "news"])
            copilot_start = payload.get("copilot_start") or {}
            self.assertIsInstance(copilot_start.get("brief_of_day"), dict)
            self.assertEqual(copilot_start.get("ask", [])[0]["id"], "portfolio_today")

    def test_market_context_cache_backfills_copilot_start_for_fresh_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cache_file = tmp / "market_context_snapshot.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "regime": "NORMAL",
                        "confidence": 0.41,
                        "key_drivers": [],
                        "characteristics": {"volatility": "medium"},
                        "recommended_layout": {"primary_widgets": ["intelligence"]},
                        "timestamp": MODULE._now().isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            brief = {
                "title": "Brief quotidien",
                "summary": "mot " * 250,
                "market_sentiment": "MIXED",
                "top_signals": [{"ticker": "AAPL"}],
                "top_risks": [{"ticker": "TSLA"}],
                "macro_signals": [{"topic": "Rates"}],
                "sector_rotation": {"top": ["Technology"], "bottom": ["Energy"]},
                "generated_at": "2026-03-01T10:00:00Z",
                "source": ["brief_daily_snapshot"],
            }

            with mock.patch.object(MODULE, "CACHE_FILE_CONTEXT", cache_file), mock.patch.object(
                MODULE, "_load_forecasts", return_value=[]
            ), mock.patch.object(MODULE, "_load_news", return_value=[]), mock.patch.object(
                MODULE, "_load_brief", return_value=brief
            ):
                payload = MODULE.get_market_context_snapshot(use_cache=True, persist=True)

            copilot_start = payload.get("copilot_start") or {}
            brief_of_day = copilot_start.get("brief_of_day") or {}
            self.assertEqual(brief_of_day.get("market_sentiment"), "MIXED")
            self.assertEqual(brief_of_day.get("source"), ["brief_daily_snapshot"])
            self.assertEqual([item.get("target") for item in copilot_start.get("open", [])], ["market", "opportunities", "copilot"])
            self.assertLessEqual(len(str(brief_of_day.get("summary", "")).split()), 200)

            persisted = json.loads(cache_file.read_text(encoding="utf-8"))
            self.assertIn("copilot_start", persisted)

    def test_market_context_start_payload_remains_never_empty_without_brief(self) -> None:
        with mock.patch.object(MODULE, "_load_forecasts", return_value=[]), mock.patch.object(
            MODULE, "_load_news", return_value=[]
        ), mock.patch.object(MODULE, "_load_brief", return_value={}):
            payload = MODULE.get_market_context_snapshot(use_cache=False, persist=False)

        copilot_start = payload.get("copilot_start") or {}
        brief_of_day = copilot_start.get("brief_of_day") or {}
        self.assertEqual(brief_of_day.get("summary"), "No daily brief available yet.")
        self.assertEqual(brief_of_day.get("source"), ["brief_daily_fallback"])
        self.assertEqual(copilot_start.get("ask", [])[0]["prompt"], "What should I do with my portfolio today?")
        self.assertEqual(copilot_start.get("open", [])[0]["target"], "market")

    def test_load_brief_supports_canonical_daily_snapshot(self) -> None:
        with mock.patch.object(
            MODULE,
            "load_json",
            return_value={
                "data": {
                    "daily": {
                        "summary": "Daily brief ready.",
                        "market_sentiment": "BULLISH",
                    }
                }
            },
        ):
            brief = MODULE._load_brief()

        self.assertEqual(brief.get("summary"), "Daily brief ready.")
        self.assertEqual(brief.get("market_sentiment"), "BULLISH")


if __name__ == "__main__":
    unittest.main()
