from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "state_reconciler.py"
SPEC = importlib.util.spec_from_file_location("fc_state_reconciler", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_state_reconciler"] = MODULE
SPEC.loader.exec_module(MODULE)
ReconcileConfig = MODULE.ReconcileConfig
run_reconciler = MODULE.run_reconciler


class StateReconcilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        self.queue_path = orch / "priority-queue.json"
        self.board_path = orch / "parallel-workstreams.json"
        self.report_path = orch / "state-reconcile-report.json"
        self.state_dir = self.root / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.lock_dir = self.root / "locks"
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _config(self) -> ReconcileConfig:
        return ReconcileConfig(
            root=self.root,
            role="planner",
            queue_path=self.queue_path,
            board_path=self.board_path,
            state_dir=self.state_dir,
            report_path=self.report_path,
            lock_dir=self.lock_dir,
            stale_lock_seconds=60,
            stale_in_progress_seconds=300,
            ready_starvation_seconds=300,
        )

    def test_parked_in_progress_is_downgraded(self) -> None:
        self.board_path.write_text(json.dumps({
            "version": "x",
            "tasks": [{"id": "BATCH-01-DEV-01", "stream_id": "BATCH-01", "role": "dev", "state": "IN_PROGRESS", "parked_by_rebuild": True, "updated_at": "2026-03-06T00:00:00Z"}],
            "streams": [{"id": "BATCH-01", "state": "IN_PROGRESS", "parked_by_rebuild": True, "updated_at": "2026-03-06T00:00:00Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-01", "state": "IN_PROGRESS", "parked_by_rebuild": True, "updated_at": "2026-03-06T00:00:00Z"}]}), encoding="utf-8")

        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1772800000)
        board = json.loads(self.board_path.read_text())
        queue = json.loads(self.queue_path.read_text())
        self.assertEqual(report["parked_inprogress_fixed"], 3)
        self.assertEqual(board["tasks"][0]["state"], "READY_DEV")
        self.assertEqual(board["streams"][0]["state"], "READY_DEV")
        self.assertEqual(queue["items"][0]["state"], "READY_DEV")

    def test_runtime_blocker_cleared_when_probes_recover(self) -> None:
        self.board_path.write_text(json.dumps({"tasks": [], "streams": [], "events": []}), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        contract = "\n".join([
            "STATUS: BLOCKED",
            "DELTA: RUNTIME_DOWN",
            "EVIDENCE: task_update=blocked; lock_check=ok; run_note=runtime down stale; issues=runtime_down; issue_count=1; issue_severity=high",
            "RISKS: runtime down",
            "NEXT: owner=admin; action=fix runtime",
            "VERDICT: BLOCKED",
            "BLOCKER_ID: RUNTIME_DOWN",
            "NEXT_ACTION_UNIQUE: X",
        ])
        (self.state_dir / "admin.last_contract").write_text(contract, encoding="utf-8")

        report = run_reconciler(self._config(), probe_runtime_ok=lambda: True, now_epoch=1772800000)
        updated = (self.state_dir / "admin.last_contract").read_text(encoding="utf-8")
        self.assertEqual(report["runtime_blockers_cleared"], 1)
        self.assertIn("BLOCKER_ID: NONE", updated)
        self.assertIn("DELTA: RUNTIME_RECOVERED_SOFT", updated)

    def test_stale_lock_removed_when_pid_is_gone(self) -> None:
        self.board_path.write_text(json.dumps({"tasks": [], "streams": [], "events": []}), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        lock = self.lock_dir / "planner.lock"
        lock.write_text("", encoding="utf-8")
        (self.lock_dir / "planner.lock.meta").write_text("pid=999999 start_epoch=1772790000\n", encoding="utf-8")

        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1772800000)
        self.assertEqual(report["stale_locks_removed"], 1)
        self.assertFalse(lock.exists())

    def test_ready_starvation_flagged(self) -> None:
        self.board_path.write_text(json.dumps({"tasks": [], "streams": [], "events": []}), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-09", "state": "READY_DEV", "updated_at": "2026-03-06T00:00:00Z"}]}), encoding="utf-8")
        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1772800000)
        queue = json.loads(self.queue_path.read_text())
        self.assertEqual(report["ready_starvation_detected"], 1)
        self.assertTrue(queue["items"][0]["ready_starvation"])

    def test_stale_in_progress_is_marked_and_downgraded(self) -> None:
        self.board_path.write_text(json.dumps({
            "version": "x",
            "tasks": [{"id": "BATCH-02-PLAN", "stream_id": "BATCH-02", "role": "planner", "state": "IN_PROGRESS", "updated_at": "2026-03-06T00:00:00Z"}],
            "streams": [{"id": "BATCH-02", "state": "IN_PROGRESS", "updated_at": "2026-03-06T00:00:00Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-02", "state": "IN_PROGRESS", "updated_at": "2026-03-06T00:00:00Z"}]}), encoding="utf-8")
        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1772800000)
        board = json.loads(self.board_path.read_text())
        self.assertEqual(report["stale_inprogress_marked"], 1)
        self.assertEqual(board["tasks"][0]["state"], "READY_PLANNER")
        self.assertIn("stale_in_progress", board["tasks"][0]["stalled_reason"])

    def test_dev_in_progress_without_active_subagent_is_downgraded_early(self) -> None:
        self.board_path.write_text(json.dumps({
            "version": "x",
            "tasks": [{
                "id": "BATCH-27-DEV-02",
                "stream_id": "BATCH-27",
                "role": "dev",
                "state": "IN_PROGRESS",
                "updated_at": "2026-03-06T00:00:00Z",
                "started_at": "2026-03-06T00:00:00Z",
                "artifact": "",
                "verify": "",
                "commit_sha": "",
                "files_touched": "",
            }],
            "streams": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-06T00:00:00Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-27", "state": "IN_PROGRESS", "updated_at": "2026-03-06T00:00:00Z"}]}), encoding="utf-8")
        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1772800000)
        board = json.loads(self.board_path.read_text())
        self.assertEqual(report["stale_inprogress_marked"], 1)
        self.assertEqual(board["tasks"][0]["state"], "READY_DEV")
        self.assertEqual(board["tasks"][0]["stalled_reason"], "planner_capability_stall_no_active_subagent")

    def test_completed_task_is_repaired_to_done_state(self) -> None:
        self.board_path.write_text(json.dumps({
            "version": "x",
            "tasks": [{
                "id": "BATCH-60-DEV-02",
                "stream_id": "BATCH-60",
                "role": "dev",
                "state": "BLOCKED",
                "blocked_reason": "planner_dev_capability_failed:old_failure",
                "completed_at": "2026-03-09T05:11:49Z",
                "commit_sha": "99d0a027fc0ca7d83774db713a91f9a1eaae756b",
                "artifact": "commit=99d0a027fc0ca7d83774db713a91f9a1eaae756b",
                "verify": "before=a; after=b; test=c",
                "updated_at": "2026-03-09T05:11:49Z",
            }],
            "streams": [{"id": "BATCH-60", "state": "BLOCKED", "updated_at": "2026-03-09T05:11:49Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-60", "state": "IN_PROGRESS", "updated_at": "2026-03-09T05:11:49Z"}]}), encoding="utf-8")
        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1773033600)
        board = json.loads(self.board_path.read_text())
        self.assertEqual(report["completed_state_repaired"], 1)
        self.assertEqual(board["tasks"][0]["state"], "DONE")
        self.assertEqual(board["tasks"][0]["blocked_reason"], "")

    def test_completed_task_clears_runtime_execution_flags(self) -> None:
        self.board_path.write_text(json.dumps({
            "version": "x",
            "tasks": [{
                "id": "BATCH-12-DEV-03",
                "stream_id": "BATCH-12",
                "role": "dev",
                "state": "DONE",
                "completed_at": "2026-03-09T11:19:02Z",
                "stalled_reason": "dev_orphaned_streak:2",
                "dev_execution_state": "orphaned",
                "dev_no_progress_streak": 0,
                "dev_orphaned_streak": 2,
                "dev_invalid_result_streak": 1,
                "dev_recovery_required": True,
                "last_capability_failure_mode": "orphaned",
                "updated_at": "2026-03-09T11:19:02Z",
            }],
            "streams": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": "2026-03-09T11:19:02Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({"items": [{"id": "BATCH-12", "state": "IN_PROGRESS", "updated_at": "2026-03-09T11:19:02Z"}]}), encoding="utf-8")

        report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1773033600)
        board = json.loads(self.board_path.read_text())
        task = board["tasks"][0]

        self.assertGreaterEqual(report["completed_state_repaired"], 1)
        self.assertEqual(task["dev_execution_state"], "")
        self.assertEqual(task["stalled_reason"], "")
        self.assertEqual(task["dev_orphaned_streak"], 0)
        self.assertEqual(task["dev_invalid_result_streak"], 0)
        self.assertFalse(task["dev_recovery_required"])
        self.assertEqual(task["last_capability_failure_mode"], "")

    def test_runtime_placeholder_proof_is_not_projected_as_progress(self) -> None:
        item = {
            "task_id": "BATCH-85-DEV-03",
            "batch_id": "BATCH-85",
            "status": "retryable",
            "blocking_issue": "invalid_subagent_result:start_banner_only",
            "delivery_proof": {
                "artifact": "...",
                "verify": "before=...; after=...; test=...",
                "tests_run": "...",
                "commit_sha": "...",
                "summary": "I need to inspect the implementation first",
            },
        }

        self.assertEqual(MODULE._runtime_item_proof_fields(item), {})
        self.assertEqual(MODULE._runtime_item_proof_count(item), 0)

    def test_placeholder_task_proof_fields_are_cleared_from_projection(self) -> None:
        self.board_path.write_text(json.dumps({
            "active_cycle": {"active_batch_ids": ["BATCH-85"]},
            "tasks": [{
                "id": "BATCH-85-DEV-03",
                "stream_id": "BATCH-85",
                "role": "dev",
                "state": "IN_PROGRESS",
                "status": "IN_PROGRESS",
                "artifact": "...",
                "verify": "before=...; after=...; test=...",
                "commit_sha": "...",
                "tests_run": "...",
                "files_touched": "...",
                "proof_count": 3,
                "updated_at": "2026-04-15T06:40:16Z",
            }],
            "streams": [{"id": "BATCH-85", "state": "IN_PROGRESS", "updated_at": "2026-04-15T06:40:16Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({
            "active_cycle": {"active_batch_ids": ["BATCH-85"]},
            "items": [{"id": "BATCH-85", "state": "IN_PROGRESS", "updated_at": "2026-04-15T06:40:16Z"}],
        }), encoding="utf-8")

        run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1776239000)
        board = json.loads(self.board_path.read_text())
        task = board["tasks"][0]

        self.assertEqual(task["proof_count"], 0)
        self.assertEqual(task["artifact"], "")
        self.assertEqual(task["verify"], "")
        self.assertEqual(task["commit_sha"], "")
        self.assertEqual(task["tests_run"], "")
        self.assertEqual(task["files_touched"], "")

    def test_runtime_retryable_banner_downgrades_in_progress_task_back_to_ready_dev(self) -> None:
        self.board_path.write_text(json.dumps({
            "active_cycle": {"active_batch_ids": ["BATCH-88"]},
            "tasks": [{
                "id": "BATCH-88-DEV-01",
                "stream_id": "BATCH-88",
                "role": "dev",
                "state": "IN_PROGRESS",
                "status": "IN_PROGRESS",
                "next_action": "retry_capability",
                "dev_execution_state": "running",
                "dev_invalid_result_streak": 2,
                "updated_at": "2026-04-15T12:59:20Z",
            }],
            "streams": [{"id": "BATCH-88", "state": "IN_PROGRESS", "updated_at": "2026-04-15T12:59:20Z"}],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({
            "active_cycle": {"active_batch_ids": ["BATCH-88"]},
            "items": [{"id": "BATCH-88", "state": "IN_PROGRESS", "updated_at": "2026-04-15T12:59:20Z"}],
        }), encoding="utf-8")

        runtime_truth = {
            "event_store_primary": True,
            "latest_states": [
                {
                    "task_id": "BATCH-88-DEV-01",
                    "batch_id": "BATCH-88",
                    "status": "retryable",
                    "blocking_issue": "invalid_subagent_result:start_banner_only",
                    "next_action": "retry_capability",
                }
            ],
            "quarantined_retryable_residue": [],
        }

        with patch.object(MODULE, "build_runtime_truth_snapshot", return_value=runtime_truth):
            report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1776240000)

        board = json.loads(self.board_path.read_text())
        task = board["tasks"][0]
        self.assertEqual(report["runtime_retryable_quarantined"], 1)
        self.assertEqual(task["state"], "READY_DEV")
        self.assertEqual(task["status"], "READY_DEV")
        self.assertEqual(task["next_action"], "claim_now")
        self.assertEqual(task["dev_execution_state"], "")
        self.assertEqual(task["dev_invalid_result_streak"], 0)
        self.assertTrue(task["runtime_truth_quarantined"])

    def test_delivery_runtime_gate_clears_when_backend_health_fallback_is_ok(self) -> None:
        self.board_path.write_text(json.dumps({
            "active_cycle": {"active_batch_ids": ["BATCH-88"]},
            "tasks": [{
                "id": "BATCH-88-DEV-01",
                "stream_id": "BATCH-88",
                "role": "dev",
                "state": "READY_DEV",
                "status": "READY_DEV",
                "policy_blocker": "backend_runtime_required_before_takeover",
                "delivery_runtime_gate": {
                    "active": True,
                    "reason": "backend_runtime_required_before_takeover",
                    "delivery_backend_reason": "status_lite_unavailable",
                },
                "updated_at": "2026-04-15T13:15:07Z",
            }],
            "streams": [{
                "id": "BATCH-88",
                "state": "READY_DEV",
                "policy_blocker": "backend_runtime_required_before_takeover",
                "delivery_runtime_gate": {
                    "active": True,
                    "reason": "backend_runtime_required_before_takeover",
                    "delivery_backend_reason": "status_lite_unavailable",
                },
                "updated_at": "2026-04-15T13:15:07Z",
            }],
            "events": [],
        }), encoding="utf-8")
        self.queue_path.write_text(json.dumps({
            "active_cycle": {"active_batch_ids": ["BATCH-88"]},
            "items": [{
                "id": "BATCH-88",
                "state": "READY_DEV",
                "policy_blocker": "backend_runtime_required_before_takeover",
                "delivery_runtime_gate": {
                    "active": True,
                    "reason": "backend_runtime_required_before_takeover",
                    "delivery_backend_reason": "status_lite_unavailable",
                },
                "updated_at": "2026-04-15T13:15:07Z",
            }],
        }), encoding="utf-8")

        with patch.object(MODULE, "_fetch_local_json", return_value=None), patch.object(MODULE, "_http_status_ok", return_value=True):
            report = run_reconciler(self._config(), probe_runtime_ok=lambda: False, now_epoch=1776240300)

        board = json.loads(self.board_path.read_text())
        queue = json.loads(self.queue_path.read_text())
        self.assertEqual(report["delivery_runtime_gate_cleared"], 3)
        self.assertEqual(report["delivery_runtime_blocked"], 0)
        self.assertNotIn("delivery_runtime_gate", board["tasks"][0])
        self.assertNotIn("policy_blocker", board["tasks"][0])
        self.assertNotIn("delivery_runtime_gate", board["streams"][0])
        self.assertNotIn("policy_blocker", board["streams"][0])
        self.assertNotIn("delivery_runtime_gate", queue["items"][0])
        self.assertNotIn("policy_blocker", queue["items"][0])

    def test_delivery_backend_ready_uses_public_api_fallback_by_default(self) -> None:
        seen: list[str] = []

        def _capture(url: str, timeout: float = 1.5) -> bool:
            seen.append(url)
            return True

        with patch.object(MODULE, "_fetch_local_json", return_value=None), patch.object(MODULE, "_http_status_ok", side_effect=_capture):
            ready, reason = MODULE._delivery_backend_ready()

        self.assertTrue(ready)
        self.assertEqual(reason, "backend_health_fallback")
        self.assertEqual(seen, ["http://3.98.20.77/api/health"])


if __name__ == "__main__":
    unittest.main()
