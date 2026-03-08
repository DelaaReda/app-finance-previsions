from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "planner_orchestrator_bridge.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_orchestrator_bridge", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_orchestrator_bridge"] = MODULE
SPEC.loader.exec_module(MODULE)
apply_bridge = MODULE.apply_bridge


class PlannerOrchestratorBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        cfg_dir = self.root / "platform" / "config" / "runner"
        orch.mkdir(parents=True, exist_ok=True)
        cfg_dir.mkdir(parents=True, exist_ok=True)
        self.board_path = orch / "parallel-workstreams.json"
        self.queue_path = orch / "priority-queue.json"
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps(
                {
                    "version": "v1",
                    "roles": {
                        "planner": {"model": "gpt-5.4", "thinking": "high"},
                        "dev": {"model": "gpt-5.4", "thinking": "high"},
                        "admin": {"model": "gpt-5.4", "thinking": "medium"},
                        "scrum_master": {"model": "gpt-5.3-codex-spark", "thinking": "low"},
                    },
                    "features": {
                        "planner_orchestrator": {
                            "enabled": 1,
                            "cron_planner_only": 1,
                            "max_active": 2,
                            "default_ttl_min": 15,
                            "retry_max": 1,
                            "backend": "mock",
                            "managed_roles": ["dev", "admin", "scrum_master"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_planner_complete_is_applied_to_workboard(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-58", "state": "READY_PLANNER", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-58-PLAN", "stream_id": "BATCH-58", "role": "planner", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-58-ANALYSIS", "stream_id": "BATCH-58", "role": "planner", "state": "READY_PLANNER", "depends_on": ["BATCH-58-PLAN"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-58", "state": "READY_PLANNER", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: COMPLETE_BATCH_58_ANALYSIS",
                "EVIDENCE: task_update=complete; stream_id=BATCH-58; task_id=BATCH-58-ANALYSIS; planner_artifact=docs/operations/orchestrator/proofs/BATCH-58.md; root_cause=analysis_done; fix_applied=close_batch58_analysis; verify=before=missing; after=proof_added; test=contract_bridge; architecture_check=layer=platform; imports_ok=yes; path_target=docs/operations/orchestrator/proofs/BATCH-58.md; vision_alignment=batch=BATCH-58; target=close_analysis; impact=free_planner_slot; tests_run=SKIP(planner_doc_only); cmd=SKIP(planner_doc_only)",
                "RISKS: none",
                "NEXT: owner=planner; action=move next",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: COMPLETE_BATCH_58",
            ]
        )
        updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertIn("planner_complete:BATCH-58-ANALYSIS", payload["actions"])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-58-ANALYSIS"]["state"], "DONE")
        self.assertEqual(tasks["BATCH-58-ANALYSIS"]["verify"], "before=missing; after=proof_added; test=contract_bridge")
        self.assertIn("bridge_actions=planner_complete:BATCH-58-ANALYSIS", updated)

    def test_ready_dev_is_claimed_and_completed_via_mock_capability(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-27-DEV-02", "stream_id": "BATCH-27", "role": "dev", "state": "READY_DEV", "priority": "P1", "depends_on": ["BATCH-27-DEV-01"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_PROGRESS_REQUIRED",
                "EVIDENCE: task_update=analysis_only; run_note=dispatch dev capability now; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=dispatch dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DISPATCH_DEV_B27",
            ]
        )
        updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dispatch"]["completed"])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-27-DEV-02"]["state"], "DONE")
        self.assertEqual(tasks["BATCH-27-DEV-02"]["commit_sha"], "mock-commit-sha")
        self.assertIn("dev_dispatch:BATCH-27-DEV-02", updated)
        self.assertIn("dev_complete:BATCH-27-DEV-02", updated)

    def test_ready_admin_is_claimed_and_completed_via_mock_capability(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-28", "state": "READY_PLANNER", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-28-DEV-03", "stream_id": "BATCH-28", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-28-ADMIN-01", "stream_id": "BATCH-28", "role": "admin", "state": "READY_PLANNER", "priority": "P1", "depends_on": ["BATCH-28-DEV-03"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-28", "state": "READY_PLANNER", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_PROGRESS_REQUIRED",
                "EVIDENCE: task_update=analysis_only; run_note=dispatch admin capability now; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=dispatch admin",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DISPATCH_ADMIN_B28",
            ]
        )
        updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-28-ADMIN-01"]["state"], "DONE")
        self.assertEqual(tasks["BATCH-28-ADMIN-01"]["artifact"], "mock://artifact")
        self.assertIn("admin_dispatch:BATCH-28-ADMIN-01", updated)
        self.assertIn("admin_complete:BATCH-28-ADMIN-01", updated)

    def test_recoverable_blocked_dev_task_is_retried(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-27", "state": "BLOCKED", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {
                            "id": "BATCH-27-DEV-02",
                            "stream_id": "BATCH-27",
                            "role": "dev",
                            "state": "BLOCKED",
                            "priority": "P1",
                            "depends_on": ["BATCH-27-DEV-01"],
                            "blocked_reason": "planner_dev_capability_failed:openclaw_agent_create_failed",
                            "updated_at": "2026-03-07T00:00:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "BLOCKED", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: RETRY_DEV",
                "EVIDENCE: task_update=analysis_only; run_note=retry recoverable dev capability; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=retry dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: RETRY_DEV_B27",
            ]
        )
        _, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dispatch"]["completed"])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-27-DEV-02"]["state"], "DONE")
        self.assertEqual(tasks["BATCH-27-DEV-02"].get("blocked_reason", ""), "")

    def test_recoverable_blocked_dev_is_prioritized_before_other_ready_dev(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-27", "state": "BLOCKED", "updated_at": "2026-03-07T00:00:00Z"},
                        {"id": "BATCH-51", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {
                            "id": "BATCH-27-DEV-02",
                            "stream_id": "BATCH-27",
                            "role": "dev",
                            "state": "BLOCKED",
                            "priority": "P1",
                            "depends_on": ["BATCH-27-DEV-01"],
                            "blocked_reason": "planner_dev_capability_failed:openclaw_agent_create_failed",
                            "updated_at": "2026-03-07T00:00:00Z",
                        },
                        {"id": "BATCH-51-DEV-01", "stream_id": "BATCH-51", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-51-DEV-02", "stream_id": "BATCH-51", "role": "dev", "state": "READY_DEV", "priority": "P1", "depends_on": ["BATCH-51-DEV-01"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps(
                {
                    "items": [
                        {"id": "BATCH-27", "state": "BLOCKED", "updated_at": "2026-03-07T00:00:00Z"},
                        {"id": "BATCH-51", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: RETRY_DEV_PRIORITY",
                "EVIDENCE: task_update=analysis_only; run_note=retry blocked dev before moving on; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=retry blocked dev first",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: RETRY_PRIORITY_B27",
            ]
        )
        _, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dispatch"]["task_id"], "BATCH-27-DEV-02")

    def test_blocked_subagent_result_does_not_leave_dev_task_in_progress(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"}],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-27-DEV-02", "stream_id": "BATCH-27", "role": "dev", "state": "READY_DEV", "priority": "P1", "depends_on": ["BATCH-27-DEV-01"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DISPATCH_DEV",
                "EVIDENCE: task_update=analysis_only; run_note=dispatch dev capability now; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=dispatch dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DISPATCH_DEV_B27",
            ]
        )
        with patch.object(MODULE.subprocess, "Popen") as popen_mock:
            _, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertEqual(payload["dispatch"]["reason"], "subagent_running")
        self.assertFalse(payload["dispatch"]["completed"])
        popen_mock.assert_called_once()
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-27-DEV-02"]["state"], "IN_PROGRESS")
        self.assertEqual(tasks["BATCH-27-DEV-02"].get("blocked_reason", ""), "")

    def test_dev_dispatch_honors_requested_backend(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"}],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-27-DEV-02", "stream_id": "BATCH-27", "role": "dev", "state": "READY_DEV", "priority": "P1", "depends_on": ["BATCH-27-DEV-01"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DISPATCH_DEV",
                "EVIDENCE: task_update=analysis_only; run_note=dispatch dev capability now; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=dispatch dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DISPATCH_DEV_B27",
            ]
        )
        with patch.object(MODULE.subprocess, "Popen") as popen_mock:
            _, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertFalse(payload["dispatch"]["completed"])
        self.assertEqual(payload["dispatch"]["backend"], "openclaw")
        popen_mock.assert_called_once()

    def test_collect_finished_dev_subagent_merges_result(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-07T00:00:00Z"}],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-27-DEV-02", "stream_id": "BATCH-27", "role": "dev", "state": "IN_PROGRESS", "priority": "P1", "depends_on": ["BATCH-27-DEV-01"], "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-07T00:00:00Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_dev_finished",
                            "target_role": "dev",
                            "owner_task_id": "BATCH-27-DEV-02",
                            "parent_role": "planner",
                            "task_kind": "delivery",
                            "status": "completed",
                            "created_at": "2026-03-07T00:00:00Z",
                            "expires_at": "2026-03-07T01:00:00Z",
                            "ttl_min": 15,
                            "backend": "openclaw",
                            "backend_ref": "sessionId=abc",
                            "last_update_at": "2026-03-07T00:01:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (results_dir / "planner_dev_finished.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_finished",
                    "owner_task_id": "BATCH-27-DEV-02",
                    "status": "completed",
                    "artifact": "abc1234",
                    "verify": "before=a; after=b; test=c",
                    "tests_run": "pytest -q",
                    "commit_sha": "abc1234",
                    "files_touched": "a.py",
                    "root_cause": "x",
                    "fix_applied": "y",
                    "architecture_check": "layer=platform; imports_ok=yes; path_target=a.py",
                    "vision_alignment": "batch=BATCH-27; target=delivery; impact=done",
                }
            ),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_DISPATCH_ACTIVE",
                "EVIDENCE: task_update=analysis_only; run_note=collect dev subagent result; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=merge result",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: COLLECT_DEV_B27",
            ]
        )
        updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertTrue(payload["ok"])
        self.assertIn("dev_collect:BATCH-27-DEV-02", payload["actions"])
        self.assertIn("dev_complete:BATCH-27-DEV-02", payload["actions"])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-27-DEV-02"]["state"], "DONE")
        self.assertIn("dev_collect:BATCH-27-DEV-02", updated)

    def test_dispatch_restarts_in_progress_dev_when_no_active_subagent(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-28", "state": "IN_PROGRESS", "updated_at": "2026-03-07T00:00:00Z"}],
                    "tasks": [
                        {"id": "BATCH-28-DEV-01", "stream_id": "BATCH-28", "role": "dev", "state": "IN_PROGRESS", "priority": "P1", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-28", "state": "IN_PROGRESS", "updated_at": "2026-03-07T00:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_DISPATCH_ACTIVE",
                "EVIDENCE: task_update=analysis_only; run_note=resume missing dev capability; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=resume dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: RESUME_DEV_B28",
            ]
        )
        with patch.object(MODULE.subprocess, "Popen") as popen_mock:
            updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertTrue(payload["dispatch"]["dispatched"])
        self.assertEqual(payload["dispatch"]["task_id"], "BATCH-28-DEV-01")
        self.assertIn("dev_dispatch:BATCH-28-DEV-01", payload["actions"])
        popen_mock.assert_called_once()
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-28-DEV-01"]["state"], "IN_PROGRESS")
        self.assertIn("dev_dispatch:BATCH-28-DEV-01", updated)


if __name__ == "__main__":
    unittest.main()
