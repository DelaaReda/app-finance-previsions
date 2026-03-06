from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "migrate_to_planner_monolane.py"
SPEC = importlib.util.spec_from_file_location("fc_migrate_to_planner_monolane", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_migrate_to_planner_monolane"] = MODULE
SPEC.loader.exec_module(MODULE)


apply_migration = MODULE.apply_migration
rollback_migration = MODULE.rollback_migration


class MigrateToPlannerMonolaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.board_path = self.root / "parallel-workstreams.json"
        self.queue_path = self.root / "priority-queue.json"
        self.report_path = self.root / "migration-report.json"

        self.board_payload = {
            "version": 1,
            "updated_at": "2026-03-06T12:00:00Z",
            "roles": {
                "planner": {"wip_limit": 1, "can_edit": False},
                "dev": {"wip_limit": 6, "can_edit": True},
                "admin": {"wip_limit": 3, "can_edit": True},
                "scrum_master": {"wip_limit": 2, "can_edit": True},
            },
            "streams": [
                {"id": "BATCH-10", "title": "Delivery", "priority": "P1", "state": "READY_DEV"},
                {"id": "BATCH-11", "title": "Repair", "priority": "P1", "state": "IN_PROGRESS"},
            ],
            "tasks": [
                {
                    "id": "BATCH-10-DEV-01",
                    "stream_id": "BATCH-10",
                    "code": "DEV-01",
                    "title": "Implement fix",
                    "role": "dev",
                    "state": "READY_DEV",
                    "priority": "P1",
                    "depends_on": [],
                    "assignee": "",
                    "blocked_reason": "",
                    "artifacts": [],
                    "notes": [],
                    "handoff_to": "",
                    "created_at": "2026-03-06T12:00:00Z",
                    "updated_at": "2026-03-06T12:00:00Z",
                    "started_at": "",
                    "completed_at": "",
                },
                {
                    "id": "BATCH-11-ADMIN-01",
                    "stream_id": "BATCH-11",
                    "code": "ADMIN-01",
                    "title": "Repair runtime",
                    "role": "admin",
                    "state": "IN_PROGRESS",
                    "priority": "P1",
                    "depends_on": [],
                    "assignee": "admin",
                    "blocked_reason": "",
                    "artifacts": [],
                    "notes": [],
                    "handoff_to": "",
                    "created_at": "2026-03-06T12:00:00Z",
                    "updated_at": "2026-03-06T12:00:00Z",
                    "started_at": "2026-03-06T12:05:00Z",
                    "completed_at": "",
                },
                {
                    "id": "BATCH-12-PLAN",
                    "stream_id": "BATCH-12",
                    "code": "PLAN",
                    "title": "Plan",
                    "role": "planner",
                    "state": "READY_PLANNER",
                    "priority": "P1",
                    "depends_on": [],
                    "assignee": "",
                    "blocked_reason": "",
                    "artifacts": [],
                    "notes": [],
                    "handoff_to": "",
                    "created_at": "2026-03-06T12:00:00Z",
                    "updated_at": "2026-03-06T12:00:00Z",
                    "started_at": "",
                    "completed_at": "",
                },
                {
                    "id": "BATCH-09-DEV-01",
                    "stream_id": "BATCH-09",
                    "code": "DEV-01",
                    "title": "Already done",
                    "role": "dev",
                    "state": "DONE",
                    "priority": "P1",
                    "depends_on": [],
                    "assignee": "dev",
                    "blocked_reason": "",
                    "artifacts": [],
                    "notes": [],
                    "handoff_to": "",
                    "created_at": "2026-03-06T12:00:00Z",
                    "updated_at": "2026-03-06T12:00:00Z",
                    "started_at": "2026-03-06T12:01:00Z",
                    "completed_at": "2026-03-06T12:02:00Z",
                },
            ],
            "handoffs": [],
            "events": [],
        }
        self.queue_payload = {
            "updated_at": "2026-03-06T12:00:00Z",
            "items": [
                {"id": "BATCH-10", "title": "Delivery", "state": "READY_DEV", "owner_role": "dev"},
                {"id": "BATCH-11", "title": "Repair", "state": "IN_PROGRESS", "owner_role": "admin"},
                {"id": "BATCH-12", "title": "Plan", "state": "READY_PLANNER", "owner_role": "planner"},
                {"id": "BATCH-09", "title": "Closed", "state": "CLOSED", "owner_role": "dev"},
                {"id": "BATCH-13", "title": "No owner", "state": "PLANNED", "owner_role": ""},
            ],
        }

        self.board_path.write_text(json.dumps(self.board_payload, indent=2) + "\n", encoding="utf-8")
        self.queue_path.write_text(json.dumps(self.queue_payload, indent=2) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _read_board(self) -> dict:
        return json.loads(self.board_path.read_text(encoding="utf-8"))

    def _read_queue(self) -> dict:
        return json.loads(self.queue_path.read_text(encoding="utf-8"))

    def _report(self) -> dict:
        return json.loads(self.report_path.read_text(encoding="utf-8"))

    def test_dry_run_reports_without_modifying_files(self) -> None:
        original_board = self.board_path.read_text(encoding="utf-8")
        original_queue = self.queue_path.read_text(encoding="utf-8")

        rc = apply_migration(self.board_path, self.queue_path, self.report_path, dry_run=True)

        self.assertEqual(rc, 0)
        self.assertEqual(self.board_path.read_text(encoding="utf-8"), original_board)
        self.assertEqual(self.queue_path.read_text(encoding="utf-8"), original_queue)

        report = self._report()
        self.assertEqual(report["mode"], "dry_run")
        self.assertEqual(report["counts"]["task_changes"], 2)
        self.assertEqual(report["counts"]["queue_changes"], 3)

    def test_apply_reassigns_open_work_to_planner(self) -> None:
        rc = apply_migration(self.board_path, self.queue_path, self.report_path, dry_run=False)

        self.assertEqual(rc, 0)
        board = self._read_board()
        queue = self._read_queue()

        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-10-DEV-01"]["role"], "planner")
        self.assertEqual(tasks["BATCH-10-DEV-01"]["state"], "READY_PLANNER")
        self.assertEqual(
            tasks["BATCH-10-DEV-01"]["meta"]["planner_monolane"]["planner_subagent_target_role"],
            "dev",
        )

        self.assertEqual(tasks["BATCH-11-ADMIN-01"]["role"], "planner")
        self.assertEqual(tasks["BATCH-11-ADMIN-01"]["state"], "READY_PLANNER")
        self.assertEqual(tasks["BATCH-11-ADMIN-01"]["assignee"], "")
        self.assertEqual(
            tasks["BATCH-11-ADMIN-01"]["meta"]["planner_monolane"]["planner_subagent_target_role"],
            "admin",
        )

        self.assertEqual(tasks["BATCH-12-PLAN"]["role"], "planner")
        self.assertEqual(tasks["BATCH-12-PLAN"]["state"], "READY_PLANNER")
        self.assertNotIn("meta", tasks["BATCH-12-PLAN"])

        self.assertEqual(tasks["BATCH-09-DEV-01"]["role"], "dev")
        self.assertEqual(tasks["BATCH-09-DEV-01"]["state"], "DONE")

        items = {item["id"]: item for item in queue["items"]}
        self.assertEqual(items["BATCH-10"]["owner_role"], "planner")
        self.assertEqual(items["BATCH-10"]["state"], "READY_PLANNER")
        self.assertEqual(items["BATCH-11"]["owner_role"], "planner")
        self.assertEqual(items["BATCH-12"]["owner_role"], "planner")
        self.assertEqual(items["BATCH-13"]["owner_role"], "planner")
        self.assertEqual(items["BATCH-09"]["owner_role"], "dev")

    def test_rollback_restores_original_role_and_state(self) -> None:
        rc = apply_migration(self.board_path, self.queue_path, self.report_path, dry_run=False)
        self.assertEqual(rc, 0)

        rc = rollback_migration(self.board_path, self.queue_path, self.report_path)
        self.assertEqual(rc, 0)

        board = self._read_board()
        queue = self._read_queue()
        tasks = {task["id"]: task for task in board["tasks"]}
        items = {item["id"]: item for item in queue["items"]}

        self.assertEqual(tasks["BATCH-10-DEV-01"]["role"], "dev")
        self.assertEqual(tasks["BATCH-10-DEV-01"]["state"], "READY_DEV")
        self.assertEqual(tasks["BATCH-11-ADMIN-01"]["role"], "admin")
        self.assertEqual(tasks["BATCH-11-ADMIN-01"]["state"], "IN_PROGRESS")
        self.assertEqual(tasks["BATCH-11-ADMIN-01"]["assignee"], "admin")
        self.assertEqual(items["BATCH-10"]["owner_role"], "dev")
        self.assertEqual(items["BATCH-10"]["state"], "READY_DEV")
        self.assertEqual(items["BATCH-13"]["owner_role"], "")


if __name__ == "__main__":
    unittest.main()
