from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
