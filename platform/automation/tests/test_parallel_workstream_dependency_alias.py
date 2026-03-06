#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKSTREAM = ROOT / "scripts" / "parallel_workstream.py"


class DependencyAliasTests(unittest.TestCase):
    def test_cross_batch_dependency_is_removed_and_task_unblocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "dep-alias"},
                "roles": {},
                "streams": [
                    {"id": "BATCH-27", "state": "IN_PROGRESS"},
                    {"id": "BATCH-28", "state": "WAITING_DEP"},
                ],
                "tasks": [
                    {
                        "id": "BATCH-27-GOV_REVIEW",
                        "stream_id": "BATCH-27",
                        "role": "planner",
                        "priority": "P1",
                        "state": "DONE",
                        "depends_on": ["BATCH-27-ADMIN-01"],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                    {
                        "id": "BATCH-28-PLAN",
                        "stream_id": "BATCH-28",
                        "role": "planner",
                        "priority": "P1",
                        "state": "WAITING_DEP",
                        "depends_on": ["BATCH-27-GOV-REVIEW"],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-28",
                        "title": "BATCH-28",
                        "state": "READY",
                        "depends_on": [],
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            board_after = json.loads(board_path.read_text(encoding="utf-8"))
            plan = next(task for task in board_after["tasks"] if task.get("id") == "BATCH-28-PLAN")
            self.assertEqual(plan.get("depends_on"), [])
            self.assertEqual(plan.get("state"), "READY_PLANNER")


if __name__ == "__main__":
    unittest.main()
