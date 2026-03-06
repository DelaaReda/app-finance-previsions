#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DISPATCHER = ROOT / "platform" / "automation" / "admin_dispatcher_tick.sh"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _board_dev_in_progress(task_id: str = "BATCH-10-DEV-01") -> dict:
    return {
        "version": "test",
        "streams": [{"id": "BATCH-10", "state": "IN_PROGRESS"}],
        "tasks": [
            {
                "id": task_id,
                "stream_id": "BATCH-10",
                "role": "dev",
                "state": "IN_PROGRESS",
                "assignee": "dev",
                "handoff_to": "",
            }
        ],
        "handoffs": [],
    }


def _queue_in_progress() -> dict:
    return {
        "version": "test",
        "items": [{"id": "BATCH-10", "state": "IN_PROGRESS"}],
    }


def _queue_ready(batch_id: str = "BATCH-27") -> dict:
    return {
        "version": "test",
        "items": [{"id": batch_id, "state": "READY"}],
    }


def _board_dev_ready(task_id: str = "BATCH-27-DEV-01") -> dict:
    return {
        "version": "test",
        "streams": [{"id": "BATCH-27", "state": "READY"}],
        "tasks": [
            {
                "id": task_id,
                "stream_id": "BATCH-27",
                "role": "dev",
                "state": "READY",
                "assignee": "",
                "handoff_to": "",
            }
        ],
        "handoffs": [],
    }


def _run_dispatch(workspace: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "FC_WORKSPACE_ROOT": str(workspace),
            "FC_ADMIN_DISPATCH_QUEUE_FILE": str(workspace / "docs/operations/orchestrator/priority-queue.json"),
            "FC_ADMIN_DISPATCH_BOARD_FILE": str(workspace / "docs/operations/orchestrator/parallel-workstreams.json"),
            "FC_ADMIN_DISPATCH_EXEC_FILE": str(workspace / "docs/operations/orchestrator/executors-monitoring-latest.json"),
            "FC_ADMIN_DISPATCH_STATE_DIR": str(workspace / "state/dispatch"),
            "FC_ROLE_STATE_DIR": str(workspace / "state/role-state"),
            "FC_ADMIN_DISPATCH_LOG_FILE": str(workspace / "logs/admin.dispatch.log"),
            "FC_ADMIN_DISPATCH_TICK_LOG": str(workspace / "logs/admin.tick.log"),
            "FC_ADMIN_DISPATCH_ENABLED": "1",
            "FC_ADMIN_AUTONOMY_ENABLED": "1",
            "FC_ADMIN_STALL_TICKS_THRESHOLD": "2",
            "FC_ADMIN_AUTONOMY_MAX_ACTIONS": "2",
            "FC_ADMIN_DISPATCH_DRY_RUN": "1",
            "FC_ADMIN_PROOF_GATE_STRICT": "1",
            "AGENT_MESSAGE_BUS_ENABLED": "0",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(DISPATCHER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class AdminDispatcherAutonomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / "scripts").mkdir(parents=True, exist_ok=True)
        (self.workspace / "platform").mkdir(parents=True, exist_ok=True)
        orch = self.workspace / "docs/operations/orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        role_state = self.workspace / "state/role-state"
        role_state.mkdir(parents=True, exist_ok=True)
        _write_json(orch / "priority-queue.json", _queue_in_progress())
        _write_json(orch / "parallel-workstreams.json", _board_dev_in_progress())
        _write_json(orch / "executors-monitoring-latest.json", {"roles": {}, "summary": {}})
        (role_state / "dev.last_contract").write_text(
            "STATUS: IN_PROGRESS\n"
            "DELTA: NO_DELTA\n"
            "EVIDENCE: task_id=BATCH-10-DEV-01; stream_id=BATCH-10; task_update=none_no_signal\n",
            encoding="utf-8",
        )
        (role_state / "planner.last_contract").write_text(
            "STATUS: WAIT\nDELTA: NO_DELTA\nEVIDENCE: task_update=none_no_signal\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_stagnation_triggers_virtual_block_after_two_ticks(self) -> None:
        run1 = _run_dispatch(self.workspace)
        self.assertEqual(run1.returncode, 0, msg=run1.stderr)
        self.assertIn("status=NOOP", run1.stdout)

        run2 = _run_dispatch(self.workspace)
        self.assertEqual(run2.returncode, 0, msg=run2.stderr)
        self.assertIn("autonomy_trigger=stalled_lane", run2.stdout)

        state_file = self.workspace / "state/role-state/admin_autonomy_state.json"
        self.assertTrue(state_file.exists())
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertTrue(state.get("active"))
        self.assertEqual(state.get("trigger"), "stalled_lane")
        self.assertEqual(state.get("target_role"), "dev")
        self.assertGreaterEqual(int(state.get("streak_by_role", {}).get("dev", 0)), 2)

    def test_explicit_blocked_has_priority_over_virtual_blocked(self) -> None:
        orch = self.workspace / "docs/operations/orchestrator"
        _write_json(
            orch / "executors-monitoring-latest.json",
            {
                "roles": {"planner": {"blocker_id": "CONTRACT_GUARD_BLOCK"}},
                "summary": {"blocker_roles": ["planner"]},
            },
        )
        run = _run_dispatch(self.workspace)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("autonomy_trigger=blocked_explicit", run.stdout)
        state = json.loads((self.workspace / "state/role-state/admin_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("trigger"), "blocked_explicit")
        self.assertEqual(state.get("target_role"), "planner")

    def test_loop_guard_sets_needs_human_review_after_failsafe(self) -> None:
        state_file = self.workspace / "state/role-state/admin_autonomy_state.json"
        _write_json(
            state_file,
            {
                "cooldown_by_role": {
                    "dev|BATCH-10-DEV-01|force_tick": {"next_epoch": 0, "failures": 3}
                }
            },
        )
        orch = self.workspace / "docs/operations/orchestrator"
        _write_json(
            orch / "executors-monitoring-latest.json",
            {
                "roles": {"dev": {"blocker_id": "BLOCKED_RUNTIME"}},
                "summary": {"blocker_roles": ["dev"]},
            },
        )
        run = _run_dispatch(
            self.workspace,
            {
                "FC_ADMIN_DISPATCH_DRY_RUN": "0",
                "FC_ADMIN_DISPATCH_SYNC_PRIORITY": "0",
                "FC_ADMIN_AUTONOMY_MAX_ACTIONS": "1",
            },
        )
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertTrue(state.get("needs_human_review_by_role", {}).get("dev"))

    def test_admin_only_block_does_not_activate_takeover(self) -> None:
        orch = self.workspace / "docs/operations/orchestrator"
        _write_json(orch / "priority-queue.json", _queue_ready())
        _write_json(orch / "parallel-workstreams.json", _board_dev_ready())
        _write_json(
            orch / "executors-monitoring-latest.json",
            {
                "roles": {"admin": {"blocker_id": "runtime_services_down"}},
                "summary": {"blocker_roles": ["admin"]},
            },
        )

        run = _run_dispatch(self.workspace)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("status=OK", run.stdout)
        self.assertIn("autonomy_trigger=none", run.stdout)
        self.assertIn("autonomy_reason_code=ADMIN_ONLY_BLOCK", run.stdout)
        self.assertIn("dispatch_reason_code=READY_DEV_LANE_EMPTY", run.stdout)


if __name__ == "__main__":
    unittest.main()
