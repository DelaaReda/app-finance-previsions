from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from apps.monitor.src.aggregators.task_progress import build_active_tasks


class TaskProgressTests(unittest.TestCase):
    def test_task_progress_detects_claim_loop_without_evidence(self):
        now = datetime.now(timezone.utc)
        started_at = (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        updated_at = (now - timedelta(minutes=40)).isoformat().replace("+00:00", "Z")
        claim_1 = (now - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
        claim_2 = (now - timedelta(minutes=19)).isoformat().replace("+00:00", "Z")
        tasks = [
            {
                "task_id": "BATCH-27-DEV-01",
                "batch_id": "BATCH-27",
                "owner": "dev",
                "state": "IN_PROGRESS",
                "started_at": started_at,
                "updated_at": updated_at,
                "title": "Implement health check",
            }
        ]
        timeline = [
            {
                "ts": claim_1,
                "role": "dev",
                "action": "CLAIM",
                "task_id": "BATCH-27-DEV-01",
                "artifact_refs": [],
            },
            {
                "ts": claim_2,
                "role": "dev",
                "action": "CLAIM",
                "task_id": "BATCH-27-DEV-01",
                "artifact_refs": [],
            },
        ]

        rows = build_active_tasks(tasks=tasks, timeline=timeline, limit=20)
        self.assertTrue(rows)
        self.assertTrue(rows[0]["stalled"])
        self.assertEqual(rows[0]["stalled_reason"], "claim_loop")

    def test_task_progress_boosts_with_artifact_and_test(self):
        now = datetime.now(timezone.utc)
        started_at = (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        updated_at = (now - timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        test_ts = (now - timedelta(minutes=15)).isoformat().replace("+00:00", "Z")
        patch_ts = (now - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
        tasks = [
            {
                "task_id": "BATCH-28-DEV-01",
                "batch_id": "BATCH-28",
                "owner": "dev",
                "state": "IN_PROGRESS",
                "started_at": started_at,
                "updated_at": updated_at,
                "title": "Implement API fallback",
            }
        ]
        timeline = [
            {
                "ts": test_ts,
                "role": "dev",
                "action": "TEST",
                "task_id": "BATCH-28-DEV-01",
                "artifact_refs": ["reports/tests.txt"],
            },
            {
                "ts": patch_ts,
                "role": "dev",
                "action": "PATCH",
                "task_id": "BATCH-28-DEV-01",
                "artifact_refs": ["apps/api/src/platform/main.py"],
            },
        ]

        rows = build_active_tasks(tasks=tasks, timeline=timeline, limit=20)
        self.assertTrue(rows)
        self.assertGreaterEqual(rows[0]["progress_pct"], 60)
        self.assertTrue(rows[0]["artifact_output"])
        self.assertTrue(rows[0]["current_step"])


if __name__ == "__main__":
    unittest.main()
