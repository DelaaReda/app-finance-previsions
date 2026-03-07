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
        blocked_payload = {
            "ok": True,
            "status": "blocked",
            "summary": "blocked by runtime",
            "artifact": "none",
            "verify": "none",
            "tests_run": "SKIP(no_tests)",
            "commit_sha": "none",
            "recommended_next": "fix runtime",
            "blocking_issue": "runtime_blocked",
            "subagent_id": "planner_dev_testblocked",
        }
        with patch.object(MODULE, "run_subagent", return_value=(0, blocked_payload)), patch.object(
            MODULE, "collect_subagent", return_value=(0, {"ok": True})
        ):
            _, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertEqual(payload["dispatch"]["reason"], "subagent_blocked")
        board = json.loads(self.board_path.read_text())
        tasks = {task["id"]: task for task in board["tasks"]}
        self.assertEqual(tasks["BATCH-27-DEV-02"]["state"], "BLOCKED")
        self.assertIn("runtime_blocked", tasks["BATCH-27-DEV-02"]["blocked_reason"])

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
        seen: dict[str, str] = {}

        def _fake_run_subagent(*args, **kwargs):
            seen["backend"] = kwargs.get("backend", "")
            return 0, {
                "ok": True,
                "status": "completed",
                "root_cause": "x",
                "fix_applied": "y",
                "artifact": "abc1234",
                "verify": "before=a; after=b; test=c",
                "files_touched": "a.py",
                "tests_run": "pytest -q",
                "commit_sha": "abc1234",
                "architecture_check": "layer=platform; imports_ok=yes; path_target=a.py",
                "vision_alignment": "batch=BATCH-27; target=delivery; impact=done",
                "subagent_id": "planner_dev_backend",
            }

        with patch.object(MODULE, "run_subagent", side_effect=_fake_run_subagent), patch.object(
            MODULE, "collect_subagent", return_value=(0, {"ok": True})
        ):
            _, payload = apply_bridge(self.root, "planner", contract, "test", backend="openclaw")
        self.assertTrue(payload["dispatch"]["completed"])
        self.assertEqual(seen["backend"], "openclaw")


if __name__ == "__main__":
    unittest.main()
