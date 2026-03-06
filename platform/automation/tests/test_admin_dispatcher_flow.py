#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[3]
DISPATCHER = ROOT / "scripts" / "admin_agents_auto_dispatch_ready.sh"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_past(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_queue(items: List[Dict]) -> Dict:
    return {
        "version": "queue_test_v1",
        "updated_at": utc_now(),
        "items": items,
    }


def make_stream(batch_id: str, state: str = "READY", priority: str = "P1") -> Dict:
    return {
        "id": batch_id,
        "title": batch_id,
        "priority": priority,
        "source_state": state,
        "state": state,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "depends_on": [],
    }


def make_task(batch_id: str, code: str, role: str, state: str = "READY", depends_on: List[str] | None = None) -> Dict:
    task_id = f"{batch_id}-{code}"
    return {
        "id": task_id,
        "stream_id": batch_id,
        "code": code,
        "title": f"{batch_id} [{code}]",
        "role": role,
        "state": state,
        "priority": "P1",
        "depends_on": depends_on or [],
        "assignee": "",
        "blocked_reason": "",
        "artifacts": [],
        "notes": [],
        "handoff_to": "",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "started_at": "",
        "completed_at": "",
    }


def make_board(streams: List[Dict], tasks: List[Dict], handoffs: List[Dict] | None = None) -> Dict:
    return {
        "version": "workboard_test_v1",
        "updated_at": utc_now(),
        "sprint": {"id": "S-TEST", "goal": "dispatcher tests", "cadence_days": 14},
        "roles": {
            "planner": {"wip_limit": 2, "can_edit": True, "focus": "planning"},
            "dev": {"wip_limit": 2, "can_edit": True, "focus": "delivery"},
            "admin": {"wip_limit": 2, "can_edit": True, "focus": "ops"},
        },
        "streams": streams,
        "tasks": tasks,
        "handoffs": handoffs or [],
        "events": [],
        "dependency_mode": "NONE",
        "parallel_execution": {"mode": "LANE_BASED", "default_wip_per_lane": 2},
    }


def read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_events(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    out: List[Dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


class AdminDispatcherFlowTests(unittest.TestCase):
    def run_dispatcher(self, queue_data: Dict, board_data: Dict, extra_env: Dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        queue_file = root / "priority-queue.json"
        board_file = root / "parallel-workstreams.json"
        state_dir = root / "state"
        events_file = root / "events" / "dispatcher.jsonl"

        queue_file.write_text(json.dumps(queue_data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        board_file.write_text(json.dumps(board_data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

        env = os.environ.copy()
        env.update(
            {
                "FINANCE_COPILOT_ROOT": str(ROOT),
                "ADMIN_AGENTS_PRIORITY_QUEUE_FILE": str(queue_file),
                "ADMIN_AGENTS_WORKBOARD_FILE": str(board_file),
                "ADMIN_AGENTS_AUTO_DISPATCH_STATE_DIR": str(state_dir),
                "ADMIN_DISPATCHER_EVENTS_FILE": str(events_file),
                "ADMIN_DISPATCHER_ENABLED": "1",
                "ADMIN_DISPATCHER_MODE": "active",
                "ADMIN_DISPATCHER_SKIP_PREFLIGHT": "1",
                "ADMIN_DISPATCHER_SKIP_SYNC": "1",
                "ADMIN_DISPATCHER_SOFT_FAIL": "1",
            }
        )
        if extra_env:
            env.update(extra_env)

        run = subprocess.run(
            ["bash", str(DISPATCHER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        return run, queue_file, board_file, events_file

    def test_ready_lane_idle_claims_task(self) -> None:
        queue = make_queue([{"id": "BATCH-50", "state": "READY", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()}])
        board = make_board([make_stream("BATCH-50")], [make_task("BATCH-50", "PLAN", "planner", state="READY")])

        run, _, board_file, events_file = self.run_dispatcher(queue, board)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("status=OK", run.stdout)

        out_board = read_json(board_file)
        task = next(t for t in out_board["tasks"] if t["id"] == "BATCH-50-PLAN")
        self.assertEqual(task["state"], "IN_PROGRESS")
        self.assertEqual(task["assignee"], "planner")

        events = read_events(events_file)
        self.assertTrue(any(e["event"] == "dispatch_result" and e["result"] == "ok" for e in events))
        result_event = next(e for e in events if e.get("event") == "dispatch_result" and e.get("result") == "ok")
        self.assertIn("dispatch_reason_code", result_event)
        self.assertIn("stream_fairness_slot", result_event)

    def test_multi_ready_selects_deterministic_priority(self) -> None:
        queue = make_queue(
            [
                {"id": "BATCH-61", "state": "READY", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()},
                {"id": "BATCH-62", "state": "READY", "priority": "P0", "created_at": utc_now(), "updated_at": utc_now()},
            ]
        )
        board = make_board(
            [make_stream("BATCH-61", priority="P1"), make_stream("BATCH-62", priority="P0")],
            [
                make_task("BATCH-61", "PLAN", "planner", state="READY"),
                make_task("BATCH-62", "PLAN", "planner", state="READY"),
            ],
        )

        run, _, board_file, _ = self.run_dispatcher(queue, board, {"ADMIN_DISPATCHER_MAX_ACTIONS_PER_TICK": "1"})
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertNotIn("status=BLOCKED", run.stdout)

        out_board = read_json(board_file)
        task_p0 = next(t for t in out_board["tasks"] if t["id"] == "BATCH-62-PLAN")
        task_p1 = next(t for t in out_board["tasks"] if t["id"] == "BATCH-61-PLAN")
        self.assertEqual(task_p0["state"], "IN_PROGRESS")
        self.assertIn(task_p1["state"], {"READY", "READY_PLANNER"})

    def test_open_handoff_stale_restarts_target_lane(self) -> None:
        queue = make_queue([{"id": "BATCH-70", "state": "IN_PROGRESS", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()}])
        board = make_board(
            [make_stream("BATCH-70", state="IN_PROGRESS")],
            [make_task("BATCH-70", "DEV-01", "dev", state="READY")],
            handoffs=[
                {
                    "id": "HO-TEST-70",
                    "from_task": "BATCH-70-ARCH",
                    "from_role": "planner",
                    "to_role": "dev",
                    "status": "OPEN",
                    "created_at": utc_past(60),
                    "updated_at": utc_past(60),
                }
            ],
        )

        run, _, board_file, events_file = self.run_dispatcher(queue, board, {"ADMIN_DISPATCHER_HANDOFF_STALE_S": "1"})
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("status=OK", run.stdout)

        out_board = read_json(board_file)
        task = next(t for t in out_board["tasks"] if t["id"] == "BATCH-70-DEV-01")
        self.assertEqual(task["state"], "IN_PROGRESS")

        events = read_events(events_file)
        self.assertTrue(
            any(
                e.get("event") == "dispatch_result"
                and e.get("reason_code") == "OPEN_HANDOFF_STALE"
                and e.get("result") == "ok"
                for e in events
            )
        )

    def test_cooldown_traces_noop(self) -> None:
        queue = make_queue([{"id": "BATCH-80", "state": "READY", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()}])
        board = make_board([make_stream("BATCH-80")], [make_task("BATCH-80", "PLAN", "planner", state="READY")])

        run1, _, board_file, events_file = self.run_dispatcher(queue, board, {"ADMIN_DISPATCHER_COOLDOWN_S": "9999"})
        self.assertEqual(run1.returncode, 0, msg=run1.stderr)
        self.assertIn("status=OK", run1.stdout)

        # Re-open the same task immediately to force cooldown path on second run.
        reopened = read_json(board_file)
        task = next(t for t in reopened["tasks"] if t["id"] == "BATCH-80-PLAN")
        task["state"] = "READY"
        task["assignee"] = ""
        task["updated_at"] = utc_now()
        board_file.write_text(json.dumps(reopened, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

        env = {
            "FINANCE_COPILOT_ROOT": str(ROOT),
            "ADMIN_AGENTS_PRIORITY_QUEUE_FILE": str((board_file.parent / "priority-queue.json")),
            "ADMIN_AGENTS_WORKBOARD_FILE": str(board_file),
            "ADMIN_AGENTS_AUTO_DISPATCH_STATE_DIR": str(board_file.parent / "state"),
            "ADMIN_DISPATCHER_EVENTS_FILE": str(events_file),
            "ADMIN_DISPATCHER_ENABLED": "1",
            "ADMIN_DISPATCHER_MODE": "active",
            "ADMIN_DISPATCHER_SKIP_PREFLIGHT": "1",
            "ADMIN_DISPATCHER_SKIP_SYNC": "1",
            "ADMIN_DISPATCHER_SOFT_FAIL": "1",
            "ADMIN_DISPATCHER_COOLDOWN_S": "9999",
        }
        run2 = subprocess.run(
            ["bash", str(DISPATCHER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, **env},
        )
        self.assertEqual(run2.returncode, 0, msg=run2.stderr)
        self.assertIn("status=NOOP", run2.stdout)
        self.assertIn("reason=COOLDOWN_ACTIVE", run2.stdout)

        events = read_events(events_file)
        self.assertTrue(any(e.get("reason_code") == "COOLDOWN_ACTIVE" for e in events))

    def test_claim_failure_is_soft(self) -> None:
        queue = make_queue([{"id": "BATCH-90", "state": "READY", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()}])
        board = make_board(
            [make_stream("BATCH-90")],
            [
                make_task("BATCH-90", "PLAN", "planner", state="READY", depends_on=["BATCH-90-MISSING"]),
                {
                    **make_task("BATCH-90", "PLAN-LEGACY", "planner", state="IN_PROGRESS"),
                    "assignee": "external_lane",  # keep lane_busy=false while serial-guard remains active
                },
            ],
        )

        run, _, _, events_file = self.run_dispatcher(queue, board)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("status=WARN", run.stdout)
        self.assertIn("reason=CLAIM_FAILED_SOFT", run.stdout)

        events = read_events(events_file)
        self.assertTrue(
            any(
                e.get("event") == "dispatch_result"
                and e.get("reason_code") == "CLAIM_FAILED_SOFT"
                and e.get("result") in {"blocked_soft", "warn"}
                for e in events
            )
        )

    def test_dependency_unsatisfied_no_action(self) -> None:
        queue = make_queue([{"id": "BATCH-91", "state": "READY", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()}])
        board = make_board(
            [make_stream("BATCH-91")],
            [make_task("BATCH-91", "PLAN", "planner", state="WAITING_DEP", depends_on=["BATCH-91-ANALYSIS"])],
        )

        run, _, board_file, events_file = self.run_dispatcher(queue, board)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("status=NOOP", run.stdout)
        self.assertIn("reason=NO_ACTIONABLE_READY", run.stdout)

        out_board = read_json(board_file)
        task = next(t for t in out_board["tasks"] if t["id"] == "BATCH-91-PLAN")
        self.assertEqual(task["state"], "WAITING_DEP")

        events = read_events(events_file)
        self.assertTrue(any(e.get("reason_code") == "NO_ACTIONABLE_READY" for e in events))

    def test_fairness_starvation_relief_promotes_waiting_stream(self) -> None:
        queue = make_queue(
            [
                {"id": "BATCH-101", "state": "READY", "priority": "P0", "created_at": utc_now(), "updated_at": utc_now()},
                {"id": "BATCH-102", "state": "READY", "priority": "P2", "created_at": utc_now(), "updated_at": utc_now()},
            ]
        )
        board = make_board(
            [make_stream("BATCH-101", priority="P0"), make_stream("BATCH-102", priority="P2")],
            [
                make_task("BATCH-101", "PLAN", "planner", state="READY"),
                make_task("BATCH-102", "PLAN", "planner", state="READY"),
            ],
        )

        # First run: high priority stream claimed.
        run1, _, board_file, events_file = self.run_dispatcher(
            queue,
            board,
            {
                "ADMIN_DISPATCHER_MAX_ACTIONS_PER_TICK": "1",
                "ADMIN_DISPATCHER_FAIRNESS_MAX_STARVE_CYCLES": "1",
                "ADMIN_DISPATCHER_COOLDOWN_S": "0",
            },
        )
        self.assertEqual(run1.returncode, 0, msg=run1.stderr)

        # Re-open top stream to keep contention, then rerun with same state directory.
        reopened = read_json(board_file)
        p0_task = next(t for t in reopened["tasks"] if t["id"] == "BATCH-101-PLAN")
        p0_task["state"] = "READY"
        p0_task["assignee"] = ""
        p0_task["updated_at"] = utc_now()
        board_file.write_text(json.dumps(reopened, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

        env = {
            "FINANCE_COPILOT_ROOT": str(ROOT),
            "ADMIN_AGENTS_PRIORITY_QUEUE_FILE": str((board_file.parent / "priority-queue.json")),
            "ADMIN_AGENTS_WORKBOARD_FILE": str(board_file),
            "ADMIN_AGENTS_AUTO_DISPATCH_STATE_DIR": str(board_file.parent / "state"),
            "ADMIN_DISPATCHER_EVENTS_FILE": str(events_file),
            "ADMIN_DISPATCHER_ENABLED": "1",
            "ADMIN_DISPATCHER_MODE": "active",
            "ADMIN_DISPATCHER_SKIP_PREFLIGHT": "1",
            "ADMIN_DISPATCHER_SKIP_SYNC": "1",
            "ADMIN_DISPATCHER_SOFT_FAIL": "1",
            "ADMIN_DISPATCHER_MAX_ACTIONS_PER_TICK": "1",
            "ADMIN_DISPATCHER_FAIRNESS_MAX_STARVE_CYCLES": "1",
            "ADMIN_DISPATCHER_COOLDOWN_S": "0",
        }
        run2 = subprocess.run(
            ["bash", str(DISPATCHER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, **env},
        )
        self.assertEqual(run2.returncode, 0, msg=run2.stderr)

        out_board = read_json(board_file)
        p2_task = next(t for t in out_board["tasks"] if t["id"] == "BATCH-102-PLAN")
        self.assertIn(p2_task["state"], {"IN_PROGRESS", "READY_PLANNER"})

        events = read_events(events_file)
        self.assertTrue(
            any(
                e.get("event") == "dispatch_result"
                and e.get("dispatch_reason_code") == "FAIRNESS_STARVATION_RELIEF"
                and e.get("result") == "ok"
                for e in events
            )
        )

    def test_zero_ready_noop(self) -> None:
        queue = make_queue([{"id": "BATCH-92", "state": "WAITING_DEP", "priority": "P1", "created_at": utc_now(), "updated_at": utc_now()}])
        board = make_board([make_stream("BATCH-92", state="WAITING_DEP")], [make_task("BATCH-92", "PLAN", "planner", state="WAITING_DEP")])

        run, _, _, events_file = self.run_dispatcher(queue, board)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertIn("status=NOOP", run.stdout)
        self.assertIn("reason=NO_ACTIONABLE_READY", run.stdout)

        events = read_events(events_file)
        self.assertTrue(any(e.get("result") == "noop" for e in events))


if __name__ == "__main__":
    unittest.main()
