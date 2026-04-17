from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "health_snapshot.sh"


def _recent_iso(minutes_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


class HealthSnapshotLatestResetTests(unittest.TestCase):
    def test_health_snapshot_clears_planner_sqlite_residue_blocker_when_runtime_truth_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            automation_link = workspace / "platform" / "automation"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)
            automation_link.parent.mkdir(parents=True, exist_ok=True)
            automation_link.symlink_to(ROOT / "platform" / "automation", target_is_directory=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": []},
                        "items": [{"id": "BATCH-89", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps({"tasks": []}),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    "2026-04-15T18:20:00 [END] role=%s rc=0\n" % role,
                    encoding="utf-8",
                )

            (state_dir / "planner.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: BLOCKED",
                        "DELTA: REPAIR_ORCHESTRATION_BLOCKED_PAR_RESIDU_SQLITE",
                        "VERDICT: BLOCKED",
                        "BLOCKER_ID: SQLITE_RUNTIME_RESIDUE_ACTIVE",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            for role in ("dev", "admin"):
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            db_path = orch / "orchestration-runtime.sqlite"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE planner_graph_state (
                        task_id TEXT PRIMARY KEY,
                        batch_id TEXT,
                        cycle_id TEXT,
                        owner_role TEXT,
                        target_role TEXT,
                        status TEXT,
                        current_node TEXT,
                        checkpoint_id TEXT,
                        updated_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE orchestration_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT,
                        event_type TEXT,
                        task_id TEXT,
                        batch_id TEXT,
                        payload_json TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO planner_graph_state (
                        task_id, batch_id, cycle_id, owner_role, target_role, status,
                        current_node, checkpoint_id, updated_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "BATCH-88-DEV-01",
                        "BATCH-88",
                        "legacy-cycle",
                        "planner",
                        "dev",
                        "complete",
                        "done",
                        "ckpt-1",
                        "2026-04-15T17:00:00Z",
                        "{}",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            planner = latest["roles"]["planner"]
            self.assertEqual(planner["status"], "IDLE")
            self.assertEqual(planner["verdict"], "IDLE")
            self.assertEqual(planner["blocker_id"], "NONE")
            self.assertEqual(planner["delta"], "NO_ACTIVE_CANONICAL_WORK")
            self.assertEqual(latest.get("health_snapshot", {}).get("blocked_agents"), [])

    def test_health_snapshot_clears_planner_closed_batch_residue_blocker_when_runtime_truth_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            automation_link = workspace / "platform" / "automation"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)
            automation_link.parent.mkdir(parents=True, exist_ok=True)
            automation_link.symlink_to(ROOT / "platform" / "automation", target_is_directory=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": []},
                        "items": [{"id": "BATCH-90", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps({"tasks": []}),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    "2026-04-15T19:10:00 [END] role=%s rc=0\n" % role,
                    encoding="utf-8",
                )

            (state_dir / "planner.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: WAIT",
                        "DELTA: AUTOBATCH_BLOQUE_PAR_RESIDU_SQLITE",
                        "VERDICT: BLOCKED",
                        "BLOCKER_ID: BATCH-90-ADMIN-01",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            for role in ("dev", "admin"):
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            db_path = orch / "orchestration-runtime.sqlite"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE planner_graph_state (
                        task_id TEXT PRIMARY KEY,
                        batch_id TEXT,
                        cycle_id TEXT,
                        owner_role TEXT,
                        target_role TEXT,
                        status TEXT,
                        current_node TEXT,
                        checkpoint_id TEXT,
                        updated_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE orchestration_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT,
                        event_type TEXT,
                        task_id TEXT,
                        batch_id TEXT,
                        payload_json TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO planner_graph_state (
                        task_id, batch_id, cycle_id, owner_role, target_role, status,
                        current_node, checkpoint_id, updated_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "BATCH-90-ADMIN-01",
                        "BATCH-90",
                        "legacy-cycle",
                        "planner",
                        "admin",
                        "ready_to_merge",
                        "apply_workboard_mutation",
                        "ckpt-90",
                        "2026-04-15T19:08:09Z",
                        "{}",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            planner = latest["roles"]["planner"]
            self.assertEqual(planner["status"], "IDLE")
            self.assertEqual(planner["verdict"], "IDLE")
            self.assertEqual(planner["blocker_id"], "NONE")
            self.assertEqual(planner["delta"], "NO_ACTIVE_CANONICAL_WORK")
            self.assertEqual(latest.get("health_snapshot", {}).get("blocked_agents"), [])

    def test_health_snapshot_demotes_ambiguous_planner_no_delta_to_idle_when_canonical_runtime_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            automation_link = workspace / "platform" / "automation"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)
            automation_link.parent.mkdir(parents=True, exist_ok=True)
            automation_link.symlink_to(ROOT / "platform" / "automation", target_is_directory=True)

            (orch / "priority-queue.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": []}, "items": []}),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": []}, "tasks": []}),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    "2026-04-15T19:10:00 [END] role=%s rc=0\n" % role,
                    encoding="utf-8",
                )

            (state_dir / "planner.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: IN_PROGRESS",
                        "DELTA: NO_DELTA",
                        "VERDICT: GO_WITH_CAUTION",
                        "BLOCKER_ID: NONE",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            for role in ("dev", "admin"):
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            db_path = orch / "orchestration-runtime.sqlite"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE planner_graph_state (
                        task_id TEXT PRIMARY KEY,
                        batch_id TEXT,
                        cycle_id TEXT,
                        owner_role TEXT,
                        target_role TEXT,
                        status TEXT,
                        current_node TEXT,
                        checkpoint_id TEXT,
                        updated_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE orchestration_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT,
                        event_type TEXT,
                        task_id TEXT,
                        batch_id TEXT,
                        payload_json TEXT
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            planner = latest["roles"]["planner"]
            self.assertEqual(planner["status"], "IDLE")
            self.assertEqual(planner["verdict"], "IDLE")
            self.assertEqual(planner["blocker_id"], "NONE")
            self.assertEqual(planner["delta"], "NO_ACTIVE_CANONICAL_WORK")

    def test_health_snapshot_clears_stale_role_action_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-86"]},
                        "items": [{"id": "BATCH-86", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-86-ARCH", "state": "IN_PROGRESS", "updated_at": "2026-04-15T08:30:00Z"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            (ticks_dir / "planner.tick.log").write_text("2026-04-15T08:38:00 [END] role=planner rc=0\n", encoding="utf-8")
            (ticks_dir / "dev.tick.log").write_text("2026-03-06T10:38:00 [END] role=dev rc=0\n", encoding="utf-8")
            (ticks_dir / "admin.tick.log").write_text("2026-03-06T10:38:00 [END] role=admin rc=0\n", encoding="utf-8")

            (state_dir / "planner.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: IN_PROGRESS",
                        "DELTA: PLANNER_QUALITY_INCOMPLETE",
                        "VERDICT: GO_WITH_CAUTION",
                        "BLOCKER_ID: NONE",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (state_dir / "dev.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: PASS",
                        "DELTA: NO_DELTA",
                        "VERDICT: PASS",
                        "BLOCKER_ID: NONE",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (state_dir / "admin.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: PASS",
                        "DELTA: NO_DELTA",
                        "VERDICT: BLOCKER_RUNTIME_INFERENCE_CONFIRME",
                        "BLOCKER_ID: NONE",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            (orch / "executors-monitoring-latest.json").write_text(
                json.dumps(
                    {
                        "roles": {
                            "admin": {
                                "source": "unit_test",
                                "next_action_unique": "TAKEOVER_CLAIM_BATCH_27_DEV_01",
                                "next": "owner=admin; action=takeover claim BATCH-27-DEV-01",
                                "task_id": "BATCH-27-DEV-01",
                                "stream_id": "BATCH-27",
                                "issues": "dev_arch_check_format_invalid",
                                "issue_count": 1,
                                "issue_severity": "high",
                                "queue_version": "queue_old",
                                "workboard_version": "workboard_old",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            admin = latest["roles"]["admin"]
            self.assertEqual(admin["source"], "health_snapshot")
            self.assertEqual(admin["next_action_unique"], "none")
            self.assertEqual(admin["next"], "owner=none; action=none")
            self.assertEqual(admin["task_id"], "none")
            self.assertEqual(admin["stream_id"], "none")
            self.assertEqual(admin["issues"], "none")
            self.assertEqual(admin["issue_count"], 0)
            self.assertEqual(admin["issue_severity"], "none")
            self.assertNotEqual(admin["queue_version"], "queue_old")
            self.assertNotEqual(admin["workboard_version"], "workboard_old")

    def test_health_snapshot_downgrades_health_when_latest_summary_has_stale_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-88"]},
                        "items": [{"id": "BATCH-88", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-88-DEV-01", "state": "IN_PROGRESS", "updated_at": "2026-04-15T12:36:00Z"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    "2026-04-15T12:38:00 [END] role=%s rc=0\n" % role,
                    encoding="utf-8",
                )
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (orch / "executors-monitoring-latest.json").write_text(
                json.dumps(
                    {
                        "roles": {"planner": {"source": "unit_test"}},
                        "summary": {"stale_context_open": 2, "stale_context_roles": ["dev", "admin"]},
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            self.assertIn(latest.get("health"), {"STALE", "DEGRADED"})
            self.assertIn(latest.get("health_snapshot", {}).get("health"), {"STALE", "DEGRADED"})

    def test_health_snapshot_prefers_iteration_active_cycle_for_capability_roles(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            canonical_orch = workspace / "docs" / "operations" / "orchestrator"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            orch.mkdir(parents=True, exist_ok=True)
            canonical_orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-90"]},
                        "items": [{"id": "BATCH-90", "state": "READY_DEV"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-90-DEV-01",
                                "role": "dev",
                                "state": "IN_PROGRESS",
                                "updated_at": "2026-04-15T18:41:17Z",
                            },
                            {
                                "id": "BATCH-90-ADMIN-01",
                                "role": "admin",
                                "state": "WAITING_DEP",
                                "updated_at": "2026-04-15T18:41:17Z",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            # Force PRIMARY_ORCH resolution toward docs/, while keeping the
            # canonical iteration-role snapshot only in runtime-state/.
            (canonical_orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-90"]},
                        "items": [{"id": "BATCH-90", "state": "READY_DEV"}],
                    }
                ),
                encoding="utf-8",
            )
            (canonical_orch / "parallel-workstreams.json").write_text(
                json.dumps({"tasks": []}),
                encoding="utf-8",
            )
            (orch / "agent-iteration-issues-latest.json").write_text(
                json.dumps(
                    {
                        "roles": {
                            "dev": {
                                "source": "planner_active_cycle_check",
                                "status": "IN_PROGRESS",
                            },
                            "admin": {
                                "source": "planner_active_cycle_check",
                                "status": "WAITING_DEP",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    "2026-04-15T18:38:00 [END] role=%s rc=0\n" % role,
                    encoding="utf-8",
                )

            (state_dir / "planner.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: IN_PROGRESS",
                        "DELTA: PLANNER_DISPATCH_ACTIVE",
                        "VERDICT: GO_WITH_CAUTION",
                        "BLOCKER_ID: NONE",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            for role in ("dev", "admin"):
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["roles"]["dev"]["status"], "IN_PROGRESS")
            self.assertEqual(latest["roles"]["dev"]["verdict"], "GO_WITH_CAUTION")
            self.assertEqual(latest["roles"]["admin"]["status"], "WAITING_DEP")
            self.assertEqual(latest["roles"]["admin"]["verdict"], "WAIT")

    def test_health_snapshot_downgrades_stale_inactive_capability_roles_from_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": []},
                        "items": [{"id": "BATCH-91", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            (orch / "agent-iteration-issues-latest.json").write_text(
                json.dumps(
                    {
                        "roles": {
                            "dev": {"source": "planner_active_cycle_check", "status": "PASS"},
                            "admin": {"source": "planner_active_cycle_check", "status": "PASS"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            (ticks_dir / "planner.tick.log").write_text(
                "2026-04-15T18:58:00 [END] role=planner rc=0\n",
                encoding="utf-8",
            )
            (ticks_dir / "dev.tick.log").write_text(
                "2026-03-06T10:38:00 [END] role=dev rc=0\n",
                encoding="utf-8",
            )
            (ticks_dir / "admin.tick.log").write_text(
                "2026-03-06T10:38:00 [END] role=admin rc=0\n",
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            env = os.environ.copy()
            env["FC_WORKSPACE_ROOT"] = str(workspace)
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_MONITOR_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_GATE_API_BASE_URL"] = "http://127.0.0.1:9"
            env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.05"

            run = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["roles"]["dev"]["status"], "WAIT")
            self.assertEqual(latest["roles"]["dev"]["verdict"], "PASS")
            self.assertEqual(latest["roles"]["dev"]["delta"], "NO_ACTIVE_CAPABILITY")
            self.assertEqual(latest["roles"]["admin"]["status"], "WAIT")
            self.assertEqual(latest["roles"]["admin"]["verdict"], "PASS")
            self.assertEqual(latest["roles"]["admin"]["delta"], "NO_ACTIVE_CAPABILITY")

    def test_health_snapshot_uses_lite_status_for_widget_health(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tick_ts = _recent_iso(0)
            updates_ts = _recent_iso(0)
            done_ts = _recent_iso(5)
            in_progress_ts = _recent_iso(2)
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)

            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-90"]},
                        "items": [{"id": "BATCH-90", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-90-DEV-03", "role": "dev", "state": "DONE", "updated_at": done_ts},
                            {"id": "BATCH-90-ADMIN-01", "role": "admin", "state": "IN_PROGRESS", "updated_at": in_progress_ts},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    f"{tick_ts} [END] role={role} rc=0\n",
                    encoding="utf-8",
                )
                (state_dir / f"{role}.last_contract").write_text(
                    "\n".join(
                        [
                            "STATUS: PASS",
                            "DELTA: NO_DELTA",
                            "VERDICT: PASS",
                            "BLOCKER_ID: NONE",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/api/status?lite=1":
                        payload = {"health": "OK"}
                        self.send_response(200)
                    elif self.path == "/api/status":
                        payload = {"error": "full_status_unavailable"}
                        self.send_response(503)
                    elif self.path.startswith("/api/recommendations/daily"):
                        payload = {"status": "ok"}
                        self.send_response(200)
                    elif self.path.startswith("/api/forecasts"):
                        payload = {"status": "ok"}
                        self.send_response(200)
                    elif self.path == "/api/health":
                        payload = {
                            "ok": True,
                            "data": {
                                "status": "ok",
                                "last_updates": {
                                    "news": updates_ts,
                                    "forecasts": updates_ts,
                                },
                            },
                        }
                        self.send_response(200)
                    else:
                        payload = {"error": "not_found"}
                        self.send_response(404)
                    body = json.dumps(payload).encode("utf-8")
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, format, *args):
                    return

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                env = os.environ.copy()
                env["FC_WORKSPACE_ROOT"] = str(workspace)
                env["FC_ROLE_STATE_DIR"] = str(state_dir)
                env["FC_MONITOR_BASE_URL"] = base_url
                env["FC_GATE_API_BASE_URL"] = base_url
                env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.5"

                run = subprocess.run(
                    ["bash", str(SCRIPT)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    env=env,
                )
                self.assertEqual(run.returncode, 0, msg=run.stderr)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            latest = json.loads((orch / "executors-monitoring-latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest.get("health"), "OK")
            self.assertEqual(latest.get("critical_widget_health", {}).get("state"), "ok")
            self.assertEqual(latest.get("critical_widget_health", {}).get("widgets", {}).get("news", {}).get("updated_at"), updates_ts)


if __name__ == "__main__":
    unittest.main()
