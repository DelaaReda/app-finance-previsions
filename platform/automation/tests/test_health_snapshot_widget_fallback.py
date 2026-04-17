from __future__ import annotations

import json
import os
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


class HealthSnapshotWidgetFallbackTests(unittest.TestCase):
    def test_health_snapshot_refreshes_generated_at_and_summary_context_versions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tick_ts = _recent_iso(0)
            done_ts = _recent_iso(1)
            waiting_ts = _recent_iso(1)
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
                        "active_cycle": {"active_batch_ids": ["BATCH-91"]},
                        "items": [{"id": "BATCH-91", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-91-DEV-03", "role": "dev", "state": "DONE", "updated_at": done_ts},
                            {
                                "id": "BATCH-91-ADMIN-01",
                                "role": "admin",
                                "state": "WAITING_DEP",
                                "updated_at": waiting_ts,
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

            (orch / "executors-monitoring-latest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-15T19:32:50Z",
                        "updated_at_utc": "2026-04-15T19:32:50Z",
                        "summary": {
                            "stale_context_open": 1,
                            "stale_context_roles": ["planner"],
                            "context_versions": {
                                "queue_version": "queue_old",
                                "workboard_version": "workboard_old",
                            },
                        },
                        "roles": {
                            "planner": {
                                "queue_version": "queue_old",
                                "workboard_version": "workboard_old",
                            }
                        },
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
            planner = latest["roles"]["planner"]
            self.assertEqual(latest["generated_at"], latest["updated_at_utc"])
            self.assertEqual(
                latest["summary"]["context_versions"]["queue_version"],
                planner["queue_version"],
            )
            self.assertEqual(
                latest["summary"]["context_versions"]["workboard_version"],
                planner["workboard_version"],
            )
            self.assertEqual(latest["summary"]["stale_context_open"], 0)
            self.assertEqual(latest["summary"]["stale_context_roles"], [])

    def test_health_snapshot_uses_lite_status_for_widget_health(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tick_ts = _recent_iso(0)
            done_ts = _recent_iso(1)
            in_progress_ts = _recent_iso(1)
            updates_ts = _recent_iso(0)
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
                def do_GET(self) -> None:
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

                def log_message(self, format: str, *args) -> None:
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
            self.assertEqual(
                latest.get("critical_widget_health", {}).get("widgets", {}).get("news", {}).get("updated_at"),
                updates_ts,
            )

    def test_health_snapshot_monitor_timeout_does_not_degrade_healthy_widgets(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tick_ts = _recent_iso(0)
            updates_ts = _recent_iso(0)
            workspace = Path(td)
            orch = workspace / "logs-codex-runs" / "orchestrator-state"
            state_dir = workspace / ".state"
            ticks_dir = workspace / "logs-codex-runs" / "fc-ticks"
            orch.mkdir(parents=True, exist_ok=True)
            state_dir.mkdir(parents=True, exist_ok=True)
            ticks_dir.mkdir(parents=True, exist_ok=True)

            (orch / "priority-queue.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": []}, "items": []}),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
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
                def do_GET(self) -> None:
                    if self.path == "/api/status?lite=1":
                        return
                    if self.path.startswith("/api/recommendations/daily"):
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

                def log_message(self, format: str, *args) -> None:
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
                env["FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS"] = "0.1"

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
            self.assertEqual(
                latest.get("critical_widget_health", {}).get("widgets", {}).get("hero", {}).get("monitor_health"),
                "unknown",
            )

    def test_health_snapshot_rate_limit_with_delivery_runway_stays_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tick_ts = _recent_iso(0)
            updates_ts = _recent_iso(0)
            ready_ts = _recent_iso(1)
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
                        "active_cycle": {"active_batch_ids": ["BATCH-95"]},
                        "items": [{"id": "BATCH-95", "state": "READY_DEV"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-95-DEV-03", "role": "dev", "state": "READY_DEV", "updated_at": ready_ts},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            (state_dir / "planner.last_contract").write_text(
                "\n".join(
                    [
                        "STATUS: RATE_LIMIT_SKIP",
                        "DELTA: RATE_LIMIT_BACKOFF",
                        "VERDICT: WAIT",
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
            for role in ("planner", "dev", "admin"):
                (ticks_dir / f"{role}.tick.log").write_text(
                    f"{tick_ts} [END] role={role} rc=0\n",
                    encoding="utf-8",
                )
            (orch / "executors-monitoring-latest.json").write_text(json.dumps({"roles": {}}), encoding="utf-8")

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    if self.path == "/api/status?lite=1":
                        payload = {"health": "OK"}
                        self.send_response(200)
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

                def log_message(self, format: str, *args) -> None:
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
            snapshot = latest.get("health_snapshot", {})
            self.assertEqual(latest.get("health"), "OK")
            self.assertTrue(snapshot.get("delivery_runway_present"))
            self.assertTrue(snapshot.get("rate_limit_backoff_non_blocking"))
            self.assertEqual(snapshot.get("health_reason"), "rate_limit_backoff_non_blocking")


if __name__ == "__main__":
    unittest.main()
