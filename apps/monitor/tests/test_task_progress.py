from __future__ import annotations

import unittest

from apps.monitor.src.aggregators.task_progress import build_active_tasks


class TaskProgressTests(unittest.TestCase):
    def test_task_progress_detects_claim_loop_without_evidence(self):
        tasks = [
            {
                "task_id": "BATCH-27-DEV-01",
                "batch_id": "BATCH-27",
                "owner": "dev",
                "state": "IN_PROGRESS",
                "started_at": "2026-03-06T10:00:00Z",
                "updated_at": "2026-03-06T10:20:00Z",
                "title": "Implement health check",
            }
        ]
        timeline = [
            {
                "ts": "2026-03-06T11:10:00Z",
                "role": "dev",
                "action": "CLAIM",
                "task_id": "BATCH-27-DEV-01",
                "artifact_refs": [],
            },
            {
                "ts": "2026-03-06T11:11:00Z",
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
        tasks = [
            {
                "task_id": "BATCH-28-DEV-01",
                "batch_id": "BATCH-28",
                "owner": "dev",
                "state": "IN_PROGRESS",
                "started_at": "2026-03-06T10:00:00Z",
                "updated_at": "2026-03-06T10:20:00Z",
                "title": "Implement API fallback",
            }
        ]
        timeline = [
            {
                "ts": "2026-03-06T11:05:00Z",
                "role": "dev",
                "action": "TEST",
                "task_id": "BATCH-28-DEV-01",
                "artifact_refs": ["reports/tests.txt"],
            },
            {
                "ts": "2026-03-06T11:00:00Z",
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
