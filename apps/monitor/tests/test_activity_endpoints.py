from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"


def _load_server_module(workspace: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    os.environ["FC_MONITOR_STATE_DIR"] = str(workspace / "state")
    os.environ["FC_MONITOR_ACTIVITY_FEED_ENABLED"] = "1"
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_activity_{id(workspace)}", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


class MonitorActivityEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        queue = {
            "items": [
                {"id": "BATCH-27", "state": "READY", "title": "Batch 27"},
                {"id": "BATCH-28", "state": "WAITING_DEP", "title": "Batch 28"},
            ]
        }
        workboard = {
            "tasks": [
                {
                    "id": "BATCH-27-DEV-01",
                    "stream_id": "BATCH-27",
                    "state": "IN_PROGRESS",
                    "role": "dev",
                    "assignee": "dev",
                    "title": "Patch runtime",
                    "depends_on": [],
                    "started_at": "2026-03-06T10:00:00Z",
                    "updated_at": "2026-03-06T11:00:00Z",
                },
                {
                    "id": "BATCH-28-DEV-01",
                    "stream_id": "BATCH-28",
                    "state": "WAITING_DEP",
                    "role": "dev",
                    "assignee": "dev",
                    "title": "Ship feature",
                    "depends_on": ["BATCH-27-DEV-01"],
                    "updated_at": "2026-03-06T11:05:00Z",
                },
            ]
        }
        (orch / "priority-queue.json").write_text(json.dumps(queue), encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text(json.dumps(workboard), encoding="utf-8")
        (orch / "events.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "at": "2026-03-06T11:05:00Z",
                            "kind": "claim",
                            "details": {"role": "dev", "task_id": "BATCH-27-DEV-01"},
                        }
                    ),
                    json.dumps(
                        {
                            "at": "2026-03-06T11:10:00Z",
                            "kind": "complete",
                            "details": {
                                "role": "dev",
                                "task_id": "BATCH-27-DEV-01",
                                "artifact": "apps/api/src/platform/main.py",
                            },
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "state").mkdir(parents=True, exist_ok=True)
        (self.root / "state" / "planner.last_contract").write_text(
            "NEXT: owner=planner; action=claim BATCH-27-ANALYSIS\n"
            "EVIDENCE: root_cause=deps; fix_applied=sync_priority; verify=queue_ok\n",
            encoding="utf-8",
        )
        (self.root / "state" / "dev.last_contract").write_text(
            "NEXT: owner=dev; action=progress BATCH-27-DEV-01\n"
            "EVIDENCE: root_cause=api_bug; fix_applied=patch; verify=test_ok\n",
            encoding="utf-8",
        )
        self.module = _load_server_module(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_contains_activity_summary(self):
        payload = self.module.status()
        self.assertIn("activity_summary", payload)
        self.assertIn("events_last_1h", payload["activity_summary"])
        self.assertIn("current_bottleneck", payload["activity_summary"])

    def test_activity_endpoints_shape(self):
        try:
            from fastapi.testclient import TestClient
        except ModuleNotFoundError as exc:
            if str(exc).startswith("No module named"):
                raise unittest.SkipTest("fastapi testclient not installed")
            raise
        client = TestClient(self.module.app)

        activity = client.get("/api/agent-activity?window=6h&limit=120")
        self.assertEqual(activity.status_code, 200)
        payload = activity.json()
        self.assertIn("timeline", payload)
        self.assertIn("throughput", payload)
        self.assertIn("intentions", payload)
        self.assertIn("dependencies", payload)

        agents_activity = client.get("/api/agents/activity")
        self.assertEqual(agents_activity.status_code, 200)
        ap = agents_activity.json()
        self.assertIn("roles", ap)
        self.assertIn("active_helper_count", ap)
        self.assertIn("planner", ap["roles"])
        self.assertIn("dev", ap["roles"])
        self.assertIn("action_summary", ap["roles"]["planner"])
        self.assertIn("recent_events", ap["roles"]["dev"])

        tasks = client.get("/api/tasks/active?window=6h&limit=50")
        self.assertEqual(tasks.status_code, 200)
        tp = tasks.json()
        self.assertIn("items", tp)
        self.assertIn("tasks", tp)
        if tp["items"]:
            self.assertIn("progress_pct", tp["items"][0])
            self.assertIn("current_step", tp["items"][0])

        dep = client.get("/api/dependencies/map?limit=200")
        self.assertEqual(dep.status_code, 200)
        dp = dep.json()
        self.assertIn("summary", dp)
        self.assertIn("bottlenecks", dp)

        access = client.get("/api/monitor/access")
        self.assertEqual(access.status_code, 200)
        ax = access.json()
        self.assertIn("canonical_ui_url", ax)
        self.assertIn("canonical_status_url", ax)
        self.assertIn("vm_local_ui_url", ax)

        html = client.get("/")
        self.assertEqual(html.status_code, 200)
        body = html.text
        self.assertIn("/api/status?lite=1", body)
        self.assertIn("/api/runtime-diagnostics?lite=1", body)
        self.assertIn("/api/monitor/access", body)
        self.assertIn("Vue Live Canonique", body)
        self.assertIn("status-lite first", body)


if __name__ == "__main__":
    unittest.main()
