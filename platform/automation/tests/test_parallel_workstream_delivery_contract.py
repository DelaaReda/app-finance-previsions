from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from compat.projections.parallel_workstream import _ensure_autobatch_stream_and_task


class ParallelWorkstreamDeliveryContractTests(unittest.TestCase):
    def test_autobatch_seeds_delivery_contract_on_stream_and_task(self) -> None:
        board = {"streams": [], "tasks": []}

        stream_created, task_created = _ensure_autobatch_stream_and_task(
            board,
            batch_id="BATCH-01",
            title="Portfolio first brief",
            priority="P1",
            now="2026-04-16T23:59:00Z",
            novelty_target="portfolio_first_brief_with_ranked_actions",
            user_visible_delta="daily brief surfaces the top action",
        )

        self.assertEqual(stream_created, 1)
        self.assertEqual(task_created, 1)
        stream = board["streams"][0]
        task = board["tasks"][0]

        for target in (stream, task):
            self.assertIn("delivery_contract", target)
            self.assertEqual(target["value_target"], "portfolio_first_brief_with_ranked_actions")
            self.assertEqual(target["user_visible_delta"], "daily brief surfaces the top action")
            self.assertIsInstance(target["api_proof"], dict)
            self.assertIsInstance(target["ui_proof"], dict)
            self.assertEqual(target["done_when"], "public_proof_status=ok && user_visible_delta_confirmed=true")
            self.assertIn("/api/health", target["api_proof"]["expected_endpoints"])
            self.assertEqual(target["ui_proof"]["url"], "http://3.98.20.77/")


if __name__ == "__main__":
    unittest.main()
