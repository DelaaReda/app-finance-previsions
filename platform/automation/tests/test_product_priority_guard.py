from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "product_priority_guard.py"
SPEC = importlib.util.spec_from_file_location("product_priority_guard_test_module", MODULE_PATH)
assert SPEC and SPEC.loader
product_priority_guard = importlib.util.module_from_spec(SPEC)
sys.modules["product_priority_guard_test_module"] = product_priority_guard
SPEC.loader.exec_module(product_priority_guard)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class ProductPriorityGuardTests(unittest.TestCase):
    def test_product_priority_guard_blocks_when_p0_product_is_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data" / "stocks").mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)

            (root / "data" / "forecasts.json").write_text(
                json.dumps(
                    {
                        "generated_at": _iso(now),
                        "last_update": _iso(now),
                        "source": ["forecasts_route", "critical_error_fallback"],
                        "data": {"rows": [{"ticker": "AAPL", "source": ["critical_error_fallback"]}]},
                    }
                ),
                encoding="utf-8",
            )
            for rel in ("news_feed.json", "brief_daily.json", "backtests.json", "stocks/prices.json"):
                path = root / "data" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"generated_at": _iso(now), "last_update": _iso(now), "data": {}}),
                    encoding="utf-8",
                )
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "parallel-workstreams.json").write_text(json.dumps({"streams": [], "tasks": []}), encoding="utf-8")

            with patch.object(
                product_priority_guard,
                "_copilot_metrics",
                return_value={"status": "fallback", "usable": False, "fallback": True, "source_count": 0},
            ):
                metrics = product_priority_guard.build_product_value_metrics(root, api_base_url=None, now=now)

            guard = metrics["priority_guard"]
            self.assertEqual(guard["status"], "blocked")
            self.assertTrue(guard["p0_broken"])
            self.assertIn("copilot_unusable", guard["blocked_reasons"])
            self.assertIn("forecasts_invalid", guard["blocked_reasons"])

    def test_delivery_mix_exposes_product_vs_orchestration_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "streams": [
                            {"id": "BATCH-10", "state": "READY", "title": "Improve copilot answer quality"},
                            {"id": "BATCH-11", "state": "IN_PROGRESS", "title": "Fix runtime contract guard"},
                        ],
                        "tasks": [
                            {"id": "BATCH-10-DEV-01", "state": "READY", "title": "Patch forecast endpoint", "code": "DEV"},
                            {"id": "BATCH-11-PLAN", "state": "IN_PROGRESS", "title": "Clean cron lock orchestration", "code": "PLAN"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            for rel in ("data/forecasts.json", "data/news_feed.json", "data/brief_daily.json", "data/backtests.json", "data/stocks/prices.json"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"generated_at": _iso(datetime.now(timezone.utc))}), encoding="utf-8")

            with patch.object(
                product_priority_guard,
                "_copilot_metrics",
                return_value={"status": "ok", "usable": True, "fallback": False, "source_count": 3},
            ):
                metrics = product_priority_guard.build_product_value_metrics(root, api_base_url=None)

            mix = metrics["delivery_mix"]
            self.assertEqual(mix["product_active_count"], 2)
            self.assertEqual(mix["orchestration_active_count"], 2)
            self.assertEqual(mix["classified_total"], 4)
            self.assertAlmostEqual(mix["product_ratio"], 0.5, places=3)

    def test_delivery_integrity_detects_missing_commit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)

            proof_ok = proofs / "proof-ok.yaml"
            proof_ok.write_text(
                'validations:\n  tests:\n    - result: "PASS"\noutputs:\n  artifacts:\n    - "abcdef1"\n',
                encoding="utf-8",
            )
            proof_bad = proofs / "proof-bad.yaml"
            proof_bad.write_text(
                'validations:\n  tests:\n    - result: "PASS"\noutputs:\n  artifacts:\n    - "docs/notes.md"\n',
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(hours=1)),
                                "details": {
                                    "task_id": "BATCH-10-DEV-01",
                                    "artifact": "abcdef1",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/proof-ok.yaml",
                                },
                            },
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=30)),
                                "details": {
                                    "task_id": "BATCH-11-DEV-01",
                                    "artifact": "docs/notes.md",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/proof-bad.yaml",
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "degraded")
            self.assertEqual(metrics["recent_completions"], 2)
            self.assertEqual(metrics["suspicious_completion_count"], 1)
            self.assertIn("BATCH-11-DEV-01", metrics["suspicious_task_ids"])


if __name__ == "__main__":
    unittest.main()
