from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "health_snapshot.sh"


class HealthSnapshotWidgetFallbackTests(unittest.TestCase):
    def test_health_snapshot_uses_lite_status_for_widget_health(self) -> None:
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
                            {"id": "BATCH-90-DEV-03", "role": "dev", "state": "DONE", "updated_at": "2026-04-15T18:54:08Z"},
                            {"id": "BATCH-90-ADMIN-01", "role": "admin", "state": "IN_PROGRESS", "updated_at": "2026-04-15T18:56:45Z"},
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
                    "2026-04-15T18:58:00 [END] role=%s rc=0\n" % role,
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
                                    "news": "2026-04-15T18:59:24Z",
                                    "forecasts": "2026-04-15T18:59:24Z",
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
                "2026-04-15T18:59:24Z",
            )


if __name__ == "__main__":
    unittest.main()
