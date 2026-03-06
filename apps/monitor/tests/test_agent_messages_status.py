from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"
CORE_ROLES = ("planner", "dev", "admin")


def _load_server_module(workspace: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_agent_messages_{id(workspace)}", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


class MonitorAgentMessagesStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
        self.module = _load_server_module(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_exposes_agent_message_counters_and_pending_per_role(self) -> None:
        now = datetime.now(timezone.utc)
        t0 = (now - timedelta(minutes=4)).isoformat().replace("+00:00", "Z")
        t1 = (now - timedelta(minutes=3)).isoformat().replace("+00:00", "Z")
        t2 = (now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
        t3 = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        t4 = now.isoformat().replace("+00:00", "Z")
        expires = (now + timedelta(days=365)).isoformat().replace("+00:00", "Z")
        bus_events = [
            {
                "event": "message_posted",
                "ts": t0,
                "message_id": "MSG_STATUS_DEV_001",
                "from": "scrum_master",
                "targets": ["dev"],
                "priority": "high",
                "sticky": True,
                "ttl_min": 10080,
                "expires_at": expires,
                "msg": "corriger channels_read",
            },
            {
                "event": "message_posted",
                "ts": t1,
                "message_id": "MSG_STATUS_ADMIN_001",
                "from": "scrum_master",
                "targets": ["admin"],
                "priority": "normal",
                "sticky": True,
                "ttl_min": 10080,
                "expires_at": expires,
                "msg": "vérifier recovery",
            },
            {
                "event": "message_delivered",
                "ts": t2,
                "message_id": "MSG_STATUS_ADMIN_001",
                "role": "admin",
                "tick_id": "A1",
            },
            {
                "event": "message_action",
                "ts": t3,
                "message_id": "MSG_STATUS_ADMIN_001",
                "role": "admin",
                "status": "done",
                "note": "resolved",
                "tick_id": "A1",
            },
            {
                "event": "message_closed",
                "ts": t4,
                "message_id": "MSG_STATUS_ADMIN_001",
                "by": "admin",
                "reason": "resolved",
            },
        ]
        bus_path = self.root / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl"
        bus_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in bus_events) + "\n",
            encoding="utf-8",
        )

        payload = self.module.status()
        self.assertIsInstance(payload, dict)
        msg = payload.get("agent_messages", {})
        self.assertIsInstance(msg, dict)
        self.assertEqual(msg.get("open"), 1)
        self.assertGreaterEqual(msg.get("delivered_recent", 0), 1)
        self.assertGreaterEqual(msg.get("actioned_recent", 0), 1)
        self.assertGreaterEqual(msg.get("closed_recent", 0), 1)

        agents = payload.get("agents", {})
        for role in CORE_ROLES:
            self.assertIn(role, agents)
            self.assertIn("pending_messages_count", agents[role])
            self.assertIn("last_message_id", agents[role])
        self.assertEqual(agents["dev"].get("pending_messages_count"), 1)
        self.assertEqual(agents["dev"].get("last_message_id"), "MSG_STATUS_DEV_001")
        self.assertEqual(agents["admin"].get("pending_messages_count"), 0)

    def test_status_exposes_po_scrum_master_payload(self) -> None:
        payload = self.module.status()
        self.assertIn("po_scrum_master", payload)
        po = payload["po_scrum_master"]
        self.assertIsInstance(po, dict)
        self.assertEqual(po.get("name"), "po_scrum_master")
        self.assertIn("mode", po)
        self.assertIn("active", po)


if __name__ == "__main__":
    unittest.main()
