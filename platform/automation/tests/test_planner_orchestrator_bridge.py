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


    def test_dispatch_payload_exposes_live_bridge_fields(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "READY_DEV", "updated_at": "2026-03-07T00:00:00Z"}],
                    "tasks": [
                        {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {"id": "BATCH-27-DEV-02", "stream_id": "BATCH-27", "role": "dev", "state": "READY_DEV", "priority": "P1", "depends_on": ["BATCH-27-DEV-01"], "updated_at": "2026-03-07T00:00:00Z", "current_step": "progress:contract_snapshot"},
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
        contract = "
".join([
            "STATUS: IN_PROGRESS",
            "DELTA: PLANNER_PROGRESS_REQUIRED",
            "EVIDENCE: task_update=analysis_only; run_note=dispatch dev capability now; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=planner; action=dispatch dev",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: DISPATCH_DEV_B27",
        ])
        _, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        dispatch = payload.get("dispatch", {})
        self.assertTrue(dispatch.get("dispatched"))
        self.assertEqual(dispatch.get("task_id"), "BATCH-27-DEV-02")
        self.assertEqual(dispatch.get("status"), "running")
        self.assertEqual(dispatch.get("last_delivery_delta"), "none")
        self.assertTrue(dispatch.get("capability_id"))
        self.assertTrue(dispatch.get("last_heartbeat"))

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

    def test_recoverable_blocked_admin_task_is_retried(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-27", "state": "BLOCKED", "updated_at": "2026-03-07T00:00:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-27-DEV-03", "stream_id": "BATCH-27", "role": "dev", "state": "DONE", "updated_at": "2026-03-06T00:00:00Z"},
                        {
                            "id": "BATCH-27-ADMIN-01",
                            "stream_id": "BATCH-27",
                            "role": "admin",
                            "state": "BLOCKED",
                            "priority": "P1",
                            "depends_on": ["BATCH-27-DEV-03"],
                            "blocked_reason": "planner_admin_capability_failed:workspace_scope_mismatch",
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
                "DELTA: RETRY_ADMIN",
                "EVIDENCE: task_update=analysis_only; run_note=retry recoverable admin capability; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=retry admin",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: RETRY_ADMIN_B27",
            ]
        )
        _, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dispatch"]["completed"])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-27-ADMIN-01"]["state"], "DONE")
        self.assertEqual(tasks["BATCH-27-ADMIN-01"].get("blocked_reason", ""), "")

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
        self.assertGreaterEqual(popen_mock.call_count, 1)
        launcher_call = popen_mock.call_args_list[-1]
        self.assertIn("planner_subagent_manager.py", launcher_call.args[0][1])
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
        self.assertGreaterEqual(popen_mock.call_count, 1)
        launcher_call = popen_mock.call_args_list[-1]
        self.assertIn("planner_subagent_manager.py", launcher_call.args[0][1])

    def test_auto_backend_uses_env_role_mapping(self) -> None:
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
        with patch.dict(MODULE.os.environ, {"FC_PLANNER_ORCHESTRATOR_BACKEND_BY_ROLE": "dev=mock,admin=codex_exec"}, clear=False):
            updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="auto")
        self.assertIn("dev_dispatch:BATCH-27-DEV-02", payload["actions"])
        self.assertEqual(payload["dispatch"]["backend"], "mock")
        self.assertIn("bridge_actions=dev_dispatch:BATCH-27-DEV-02", updated)

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

    def test_collect_only_merges_targeted_dev_result(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T01:54:00Z"}],
                    "tasks": [
                        {"id": "BATCH-60-DEV-01", "stream_id": "BATCH-60", "role": "dev", "state": "IN_PROGRESS", "priority": "P1", "updated_at": "2026-03-09T01:54:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T01:54:00Z"}]}),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-09T01:57:43Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_dev_collect_only",
                            "target_role": "dev",
                            "owner_task_id": "BATCH-60-DEV-01",
                            "parent_role": "planner",
                            "task_kind": "delivery",
                            "status": "completed",
                            "created_at": "2026-03-09T01:47:18Z",
                            "expires_at": "2026-03-09T02:32:18Z",
                            "ttl_min": 45,
                            "backend": "openclaw",
                            "last_update_at": "2026-03-09T01:57:43Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (results_dir / "planner_dev_collect_only.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_collect_only",
                    "owner_task_id": "BATCH-60-DEV-01",
                    "status": "completed",
                    "artifact": "commit=abc123",
                    "verify": "before=a; after=b; test=c",
                    "tests_run": "pytest -q",
                    "commit_sha": "abc123",
                    "files_touched": "apps/api/src/example.py",
                    "root_cause": "x",
                    "fix_applied": "y",
                    "architecture_check": "layer=api; imports_ok=yes; path_target=apps/api/src/example.py",
                    "vision_alignment": "batch=BATCH-60; target=delivery; impact=advance",
                }
            ),
            encoding="utf-8",
        )
        payload = MODULE.collect_pending_results(self.root, "test", owner_task_id="BATCH-60-DEV-01", target_role="dev")
        self.assertTrue(payload["ok"])
        self.assertIn("dev_collect:BATCH-60-DEV-01", payload["actions"])
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-60-DEV-01"]
        self.assertEqual(task["state"], "DONE")

    def test_collect_only_merges_orphan_dev_result_without_registry_row(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T01:54:00Z"}],
                    "tasks": [
                        {"id": "BATCH-60-DEV-01", "stream_id": "BATCH-60", "role": "dev", "state": "IN_PROGRESS", "priority": "P1", "updated_at": "2026-03-09T01:54:00Z"},
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T01:54:00Z"}]}),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps({"updated_at": "2026-03-09T01:57:43Z", "subagents": []}), encoding="utf-8")
        (results_dir / "planner_dev_orphan.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_orphan",
                    "owner_task_id": "BATCH-60-DEV-01",
                    "status": "completed",
                    "artifact": "commit=abc123",
                    "verify": "before=a; after=b; test=c",
                    "tests_run": "pytest -q",
                    "commit_sha": "abc123",
                    "files_touched": "apps/api/src/example.py",
                    "root_cause": "x",
                    "fix_applied": "y",
                    "architecture_check": "layer=api; imports_ok=yes; path_target=apps/api/src/example.py",
                    "vision_alignment": "batch=BATCH-60; target=delivery; impact=advance",
                }
            ),
            encoding="utf-8",
        )
        payload = MODULE.collect_pending_results(self.root, "test", owner_task_id="BATCH-60-DEV-01", target_role="dev")
        self.assertTrue(payload["ok"])
        self.assertIn("orphan_dev_complete:BATCH-60-DEV-01", payload["actions"])
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-60-DEV-01"]
        self.assertEqual(task["state"], "DONE")

    def test_collect_only_unblocks_blocked_task_before_orphan_completion(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T01:54:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-60-DEV-01",
                            "stream_id": "BATCH-60",
                            "role": "dev",
                            "state": "BLOCKED",
                            "blocked_reason": "planner_dev_capability_failed:complete_merge_failed",
                            "priority": "P1",
                            "updated_at": "2026-03-09T01:54:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T01:54:00Z"}]}),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps({"updated_at": "2026-03-09T01:57:43Z", "subagents": []}), encoding="utf-8")
        (results_dir / "planner_dev_blocked.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_blocked",
                    "owner_task_id": "BATCH-60-DEV-01",
                    "status": "completed",
                    "artifact": "commit=abc123",
                    "verify": "before=a; after=b; test=c",
                    "tests_run": "pytest -q",
                    "commit_sha": "abc123",
                    "files_touched": "apps/api/src/example.py",
                    "root_cause": "x",
                    "fix_applied": "y",
                    "architecture_check": "layer=api; imports_ok=yes; path_target=apps/api/src/example.py",
                    "vision_alignment": "batch=BATCH-60; target=delivery; impact=advance",
                }
            ),
            encoding="utf-8",
        )
        payload = MODULE.collect_pending_results(self.root, "test", owner_task_id="BATCH-60-DEV-01", target_role="dev")
        self.assertTrue(payload["ok"])
        self.assertIn("orphan_dev_complete:BATCH-60-DEV-01", payload["actions"])
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-60-DEV-01"]
        self.assertEqual(task["state"], "DONE")
        self.assertEqual(task.get("blocked_reason", ""), "")

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
        self.assertGreaterEqual(popen_mock.call_count, 1)
        launcher_call = popen_mock.call_args_list[-1]
        self.assertIn("planner_subagent_manager.py", launcher_call.args[0][1])
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-28-DEV-01"]["state"], "IN_PROGRESS")
        self.assertIn("dev_dispatch:BATCH-28-DEV-01", updated)

    def test_active_admin_with_result_file_does_not_block_next_admin_dispatch(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [
                        {"id": "BATCH-11", "state": "READY_PLANNER", "updated_at": "2026-03-09T01:54:00Z"},
                    ],
                    "tasks": [
                        {"id": "BATCH-11-DEV-03", "stream_id": "BATCH-11", "role": "dev", "state": "DONE", "updated_at": "2026-03-09T01:40:00Z"},
                        {
                            "id": "BATCH-11-ADMIN-01",
                            "stream_id": "BATCH-11",
                            "role": "admin",
                            "state": "READY",
                            "priority": "P1",
                            "depends_on": ["BATCH-11-DEV-03"],
                            "updated_at": "2026-03-09T01:54:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-11", "state": "READY_PLANNER", "updated_at": "2026-03-09T01:54:00Z"}]}),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-09T01:54:48Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_admin_old",
                            "target_role": "admin",
                            "owner_task_id": "BATCH-27-ADMIN-01",
                            "parent_role": "planner",
                            "task_kind": "runtime",
                            "status": "running",
                            "created_at": "2026-03-09T01:46:54Z",
                            "expires_at": "2026-03-09T02:31:54Z",
                            "ttl_min": 45,
                            "backend": "codex_exec",
                            "last_update_at": "2026-03-09T01:46:54Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (results_dir / "planner_admin_old.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_admin_old",
                    "owner_task_id": "BATCH-27-ADMIN-01",
                    "status": "completed",
                    "artifact": "logs/runtime-proof.json",
                    "verify": "before=drift; after=ok; test=doctor",
                    "tests_run": "bash scripts/fc_doctor.sh",
                    "commit_sha": "none",
                    "files_touched": "none",
                    "root_cause": "drift",
                    "fix_applied": "repair",
                    "architecture_check": "layer=runtime; imports_ok=yes; path_target=logs/runtime-proof.json",
                    "vision_alignment": "batch=BATCH-27; target=runtime; impact=healthy",
                }
            ),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_DISPATCH_ACTIVE",
                "EVIDENCE: task_update=analysis_only; run_note=ignore collectible active admin and move next; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=dispatch admin",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DISPATCH_ADMIN_B11",
            ]
        )
        with patch.object(MODULE.subprocess, "Popen") as popen_mock:
            _, payload = apply_bridge(self.root, "planner", contract, "test", backend="auto")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dispatch"]["task_id"], "BATCH-11-ADMIN-01")
        self.assertEqual(payload["dispatch"]["backend"], "codex_exec")
        self.assertGreaterEqual(popen_mock.call_count, 1)
        launcher_call = popen_mock.call_args_list[-1]
        self.assertIn("planner_subagent_manager.py", launcher_call.args[0][1])

    def test_stale_admin_subagent_sets_takeover_after_timeout_streak(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-27-ADMIN-01",
                            "stream_id": "BATCH-27",
                            "role": "admin",
                            "state": "IN_PROGRESS",
                            "priority": "P1",
                            "admin_timeout_streak": 2,
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-08T19:00:00Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_admin_stale",
                            "target_role": "admin",
                            "owner_task_id": "BATCH-27-ADMIN-01",
                            "parent_role": "planner",
                            "task_kind": "runtime",
                            "status": "running",
                            "created_at": "2026-03-08T18:40:00Z",
                            "last_update_at": "2026-03-08T18:40:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}]}),
            encoding="utf-8",
        )

        actions = MODULE._mark_stale_admin_subagents(self.root, "test")
        self.assertIn("admin_takeover_required:BATCH-27-ADMIN-01", actions)
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-27-ADMIN-01"]
        self.assertTrue(task["planner_takeover_required"])
        self.assertEqual(task["admin_timeout_streak"], 3)
        self.assertIn(task["state"], {"READY", "READY_PLANNER"})

    def test_long_running_dev_subagent_is_not_requeued_without_no_progress(self) -> None:
        recent = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": recent}],
                    "tasks": [
                        {
                            "id": "BATCH-12-DEV-01",
                            "stream_id": "BATCH-12",
                            "role": "dev",
                            "state": "IN_PROGRESS",
                            "priority": "P1",
                            "updated_at": recent,
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": recent,
                    "subagents": [
                        {
                            "subagent_id": "planner_dev_stale",
                            "target_role": "dev",
                            "owner_task_id": "BATCH-12-DEV-01",
                            "parent_role": "planner",
                            "task_kind": "delivery",
                            "backend": "openclaw",
                            "status": "running",
                            "created_at": recent,
                            "last_update_at": recent,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": recent}]}),
            encoding="utf-8",
        )

        with patch.object(MODULE, "_openclaw_agent_ids", return_value={"planner_dev_stale"}):
            actions = MODULE._mark_stale_dev_subagents(self.root, "test")
        self.assertEqual(actions, [])
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-12-DEV-01"]
        self.assertFalse(task.get("dev_recovery_required"))
        self.assertEqual(task.get("dev_execution_state"), "running")
        self.assertEqual(task["state"], "IN_PROGRESS")

    def test_no_progress_dev_subagent_sets_recovery_required_after_threshold(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-12-DEV-01",
                            "stream_id": "BATCH-12",
                            "role": "dev",
                            "state": "IN_PROGRESS",
                            "priority": "P1",
                            "dev_no_progress_streak": 1,
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-08T19:00:00Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_dev_stale",
                            "target_role": "dev",
                            "owner_task_id": "BATCH-12-DEV-01",
                            "parent_role": "planner",
                            "task_kind": "delivery",
                            "backend": "openclaw",
                            "status": "running",
                            "created_at": "2026-03-08T18:40:00Z",
                            "last_update_at": "2026-03-08T18:40:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}]}),
            encoding="utf-8",
        )

        with patch.object(MODULE, "_openclaw_agent_ids", return_value={"planner_dev_stale"}):
            actions = MODULE._mark_stale_dev_subagents(self.root, "test")
        self.assertIn("dev_recovery_required:BATCH-12-DEV-01", actions)
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-12-DEV-01"]
        self.assertTrue(task["dev_recovery_required"])
        self.assertEqual(task["dev_no_progress_streak"], 2)
        self.assertEqual(task["state"], "READY_DEV")

    def test_orphaned_dev_subagent_is_requeued_immediately(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-12-DEV-01",
                            "stream_id": "BATCH-12",
                            "role": "dev",
                            "state": "IN_PROGRESS",
                            "priority": "P1",
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-08T19:00:00Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_dev_stale",
                            "target_role": "dev",
                            "owner_task_id": "BATCH-12-DEV-01",
                            "parent_role": "planner",
                            "task_kind": "delivery",
                            "backend": "openclaw",
                            "status": "running",
                            "created_at": "2026-03-08T18:40:00Z",
                            "last_update_at": "2026-03-08T18:40:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}]}),
            encoding="utf-8",
        )

        with patch.object(MODULE, "_openclaw_agent_ids", return_value=set()):
            actions = MODULE._mark_stale_dev_subagents(self.root, "test")
        self.assertIn("dev_orphaned_reset:BATCH-12-DEV-01", actions)
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-12-DEV-01"]
        self.assertTrue(task["dev_recovery_required"])
        self.assertEqual(task["dev_orphaned_streak"], 1)
        self.assertEqual(task["state"], "READY_DEV")

    def test_admin_invalid_result_sets_takeover_required_after_threshold(self) -> None:
        board = {
            "tasks": [
                {
                    "id": "BATCH-60-ADMIN-01",
                    "role": "admin",
                    "state": "IN_PROGRESS",
                    "priority": "P1",
                    "admin_invalid_result_streak": 2,
                }
            ],
            "events": [],
            "streams": [],
            "handoffs": [],
        }
        outcome = MODULE._record_admin_failure(
            board,
            task_id_value="BATCH-60-ADMIN-01",
            source="test",
            subagent_id="planner_admin_invalid",
            blocking_issue="invalid_subagent_result:start_banner_only",
            event_kind="planner_orchestrator_admin_dispatch_failed",
        )
        self.assertEqual(outcome, "planner_takeover_required")
        task = board["tasks"][0]
        self.assertTrue(task["planner_takeover_required"])
        self.assertEqual(task["admin_invalid_result_streak"], 3)

    def test_planner_takeover_admin_task_completes_after_repeated_timeouts(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-27-DEV-03",
                            "stream_id": "BATCH-27",
                            "role": "dev",
                            "state": "DONE",
                            "updated_at": "2026-03-08T18:00:00Z",
                        },
                        {
                            "id": "BATCH-27-ADMIN-01",
                            "stream_id": "BATCH-27",
                            "code": "ADMIN-01",
                            "title": "Reliability SRE Pack + Chaos Drills [ADMIN-01]",
                            "role": "admin",
                            "state": "READY",
                            "priority": "P1",
                            "depends_on": ["BATCH-27-DEV-03"],
                            "planner_takeover_required": True,
                            "admin_timeout_streak": 3,
                            "artifact": "apps/monitor/server.py",
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_DISPATCH_ACTIVE",
                "EVIDENCE: task_update=analysis_only; run_note=take over stalled admin task; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=take over admin",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: TAKEOVER_ADMIN_B27",
            ]
        )
        with (
            patch.object(
                MODULE,
                "_fetch_local_json",
                side_effect=[
                    (True, {"health": "OK"}, "ok"),
                    (True, {"status": "ok"}, "ok"),
                ],
            ),
            patch.object(MODULE, "_run_browser_validation", return_value=(True, "proofs/browser.json")),
        ):
            updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dispatch"]["reason"], "planner_takeover_completed")
        self.assertIn("admin_dispatch:BATCH-27-ADMIN-01", payload["actions"])
        self.assertIn("admin_complete:BATCH-27-ADMIN-01", payload["actions"])
        self.assertIn("DELTA: PLANNER_RECOVERY_PROGRESS", updated)
        self.assertIn("NEXT_ACTION_UNIQUE: PLANNER_RESUME_AFTER_BATCH-27-ADMIN-01", updated)
        self.assertNotIn("PLANNER_DISPATCH_ACTIVE_BATCH-27-ADMIN-01", updated)
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-27-ADMIN-01"]
        self.assertEqual(task["state"], "DONE")
        self.assertFalse(task["planner_takeover_required"])
        self.assertEqual(task["completion_mode"], "runtime_no_code")
        self.assertIn("admin_complete:BATCH-27-ADMIN-01", updated)

    def test_planner_takeover_admin_task_allows_doctor_degraded_when_critical_checks_are_ok(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-11", "state": "IN_PROGRESS", "updated_at": "2026-03-09T04:40:00Z"}],
                    "tasks": [
                        {"id": "BATCH-11-DEV-03", "stream_id": "BATCH-11", "role": "dev", "state": "DONE", "updated_at": "2026-03-09T04:30:00Z"},
                        {
                            "id": "BATCH-11-ADMIN-01",
                            "stream_id": "BATCH-11",
                            "role": "admin",
                            "state": "READY",
                            "priority": "P1",
                            "depends_on": ["BATCH-11-DEV-03"],
                            "planner_takeover_required": True,
                            "admin_timeout_streak": 3,
                            "updated_at": "2026-03-09T04:40:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-11", "state": "IN_PROGRESS", "updated_at": "2026-03-09T04:40:00Z"}]}), encoding="utf-8")
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_DISPATCH_ACTIVE",
                "EVIDENCE: task_update=analysis_only; run_note=take over admin under doctor degraded but critical checks ok; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=take over admin",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: TAKEOVER_ADMIN_B11",
            ]
        )
        degraded_doctor = {
            "status": "degraded",
            "checks": {
                "runtime_state": {"status": "ok"},
                "sessions": {"status": "ok"},
                "locks": {"status": "ok"},
                "queue_workboard": {"status": "ok"},
                "providers": {"status": "ok"},
                "product_value": {"status": "ok"},
                "qa_review_pipeline": {"status": "degraded"},
            },
        }
        with (
            patch.object(MODULE, "_fetch_local_json", side_effect=[(True, {"health": "OK"}, "ok"), (True, degraded_doctor, "ok")]),
            patch.object(MODULE, "_run_browser_validation", return_value=(False, "browser_not_required")),
        ):
            updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="auto")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dispatch"]["reason"], "planner_takeover_completed")
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-11-ADMIN-01"]
        self.assertEqual(task["state"], "DONE")
        self.assertIn("admin_complete:BATCH-11-ADMIN-01", updated)

    def test_collect_finished_admin_subagent_backfills_runtime_no_code_metadata(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-27-ADMIN-01",
                            "stream_id": "BATCH-27",
                            "role": "admin",
                            "state": "IN_PROGRESS",
                            "priority": "P1",
                            "planner_takeover_required": True,
                            "admin_timeout_streak": 2,
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        registry_path = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
        results_dir = self.root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-03-08T19:00:00Z",
                    "subagents": [
                        {
                            "subagent_id": "planner_admin_finished",
                            "target_role": "admin",
                            "owner_task_id": "BATCH-27-ADMIN-01",
                            "parent_role": "planner",
                            "task_kind": "runtime",
                            "status": "completed",
                            "created_at": "2026-03-08T19:00:00Z",
                            "last_update_at": "2026-03-08T19:05:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}]}),
            encoding="utf-8",
        )
        (results_dir / "planner_admin_finished.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_admin_finished",
                    "owner_task_id": "BATCH-27-ADMIN-01",
                    "status": "completed",
                    "artifact": "logs/runtime/admin-repair.log",
                    "verify": "before=drift; after=healthy; test=doctor",
                    "tests_run": "bash scripts/fc_doctor.sh",
                    "commit_sha": "none",
                    "files_touched": "none",
                    "root_cause": "runtime drift",
                    "fix_applied": "repair session state",
                    "architecture_check": "layer=runtime; imports_ok=yes; path_target=logs/runtime/admin-repair.log",
                    "vision_alignment": "batch=BATCH-27; target=runtime; impact=healthy",
                }
            ),
            encoding="utf-8",
        )

        actions = MODULE._collect_finished_admin_subagents(self.root, "test")
        self.assertIn("admin_complete:BATCH-27-ADMIN-01", actions)
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-27-ADMIN-01"]
        self.assertEqual(task["completion_mode"], "runtime_no_code")
        self.assertEqual(task["runtime_artifact"], "logs/runtime/admin-repair.log")
        self.assertFalse(task["planner_takeover_required"])

    def test_apply_bridge_backfills_browser_proof_for_historical_web_task(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-91", "state": "DONE", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-91-DEV-01",
                            "stream_id": "BATCH-91",
                            "role": "dev",
                            "state": "DONE",
                            "title": "Refine monitor panel",
                            "artifact": "apps/monitor/server.py",
                            "commit_sha": "abcdef1234567",
                            "tests_run": "pytest apps/monitor/tests",
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                    ],
                    "events": [
                        {
                            "kind": "complete",
                            "at": "2026-03-08T19:05:00Z",
                            "details": {
                                "task_id": "BATCH-91-DEV-01",
                                "artifact": "apps/monitor/server.py",
                                "proof_manifest": "docs/operations/orchestrator/proofs/historical-web.yaml",
                            },
                        }
                    ],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        proofs = self.root / "docs" / "operations" / "orchestrator" / "proofs"
        proofs.mkdir(parents=True, exist_ok=True)
        (proofs / "historical-web.yaml").write_text(
            'validations:\n  tests:\n    - result: "PASS"\noutputs:\n  artifacts:\n    - "apps/monitor/server.py"\n',
            encoding="utf-8",
        )
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLANNER_MONITOR",
                "EVIDENCE: task_update=analysis_only; run_note=backfill proof debt; issues=none; issue_count=0; issue_severity=none",
                "RISKS: none",
                "NEXT: owner=planner; action=monitor",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: BACKFILL_BROWSER",
            ]
        )
        with patch.object(MODULE, "run_browser_smoke", return_value={"proof_path": str(self.root / "logs-codex-runs" / "browser-smoke" / "proof.json")}):
            updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertIn("browser_backfill:BATCH-91-DEV-01:ok", payload["actions"])
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-91-DEV-01"]
        self.assertEqual(task["browser_proof_status"], "completed")

    def test_requires_browser_proof_does_not_treat_build_word_as_ui(self) -> None:
        task = {
            "title": "Build a personal finance copilot that starts with a brief of the day",
            "artifact": "",
            "files_touched": "",
            "code": "ADMIN-01",
        }
        self.assertFalse(MODULE._requires_browser_proof(task))

    def test_apply_bridge_auto_completes_planner_gov_review_when_deps_done(self) -> None:
        self.board_path.write_text(
            json.dumps(
                {
                    "version": "x",
                    "roles": {},
                    "streams": [{"id": "BATCH-28", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}],
                    "tasks": [
                        {
                            "id": "BATCH-28-ADMIN-01",
                            "stream_id": "BATCH-28",
                            "role": "admin",
                            "code": "ADMIN-01",
                            "state": "DONE",
                            "updated_at": "2026-03-08T19:00:00Z",
                        },
                        {
                            "id": "BATCH-28-GOV_REVIEW",
                            "stream_id": "BATCH-28",
                            "role": "planner",
                            "code": "GOV_REVIEW",
                            "state": "IN_PROGRESS",
                            "depends_on": ["BATCH-28-ADMIN-01"],
                            "updated_at": "2026-03-08T19:00:00Z",
                            "prechange_plan_items": ["close review"],
                            "prechange_architecture_checks": ["reuse existing state transition"],
                            "prechange_reflection_dimensions": ["scope", "verification", "rollback"],
                            "prechange_gate_version": 2,
                        },
                    ],
                    "events": [],
                    "handoffs": [],
                }
            ),
            encoding="utf-8",
        )
        self.queue_path.write_text(
            json.dumps({"items": [{"id": "BATCH-28", "state": "IN_PROGRESS", "updated_at": "2026-03-08T19:00:00Z"}]}),
            encoding="utf-8",
        )
        contract = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: RESUME_BATCH_28_GOV_REVIEW_BLOCKED",
                "EVIDENCE: task_update=blocked; run_note=gov_review blocked; issues=command_unavailable; issue_count=1; issue_severity=medium",
                "RISKS: none",
                "NEXT: owner=planner; action=complete BATCH-28-GOV_REVIEW",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: PLANNER_COMPLETE_COMMAND_UNAVAILABLE_FOR_GOV_REVIEW",
                "NEXT_ACTION_UNIQUE: COMPLETE_BATCH_28_GOV_REVIEW",
            ]
        )
        updated, payload = apply_bridge(self.root, "planner", contract, "test", backend="mock")
        self.assertTrue(payload["ok"])
        self.assertIn("planner_gov_review_auto_complete:BATCH-28-GOV_REVIEW", payload["actions"])
        board = json.loads(self.board_path.read_text())
        task = {row["id"]: row for row in board["tasks"]}["BATCH-28-GOV_REVIEW"]
        self.assertEqual(task["state"], "DONE")
        self.assertEqual(task["completion_mode"], "runtime_no_code")
        self.assertIn("planner_gov_review_auto_complete:BATCH-28-GOV_REVIEW", updated)


if __name__ == "__main__":
    unittest.main()
