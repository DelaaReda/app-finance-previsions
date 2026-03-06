from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"


def _load_server_module(workspace: Path, state_dir: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    os.environ["FC_MONITOR_STATE_DIR"] = str(state_dir)
    spec = importlib.util.spec_from_file_location(
        f"fc_monitor_server_admin_autonomy_{id(workspace)}", SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed")
        raise
    return module


class MonitorStatusAdminAutonomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
        (orch / "agent-iteration-issues.jsonl").write_text("", encoding="utf-8")
        (self.root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl").write_text("", encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)
        (self.state / "admin_autonomy_state.json").write_text(
            json.dumps(
                {
                    "active": True,
                    "trigger": "stalled_lane",
                    "target_role": "dev",
                    "target_task": "BATCH-10-DEV-01",
                    "reason_blocker": "STALLED_LANE",
                    "last_action": "force_tick",
                    "last_outcome": "partial",
                    "since_ts": "2026-03-05T10:00:00Z",
                    "streak_by_role": {"planner": 0, "dev": 2},
                    "needs_human_review_by_role": {"planner": False, "dev": False},
                },
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )
        self.module = _load_server_module(self.root, self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_exposes_admin_autonomy_block(self) -> None:
        contracts = {
            "planner": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            "dev": {"STATUS": "IN_PROGRESS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            "admin": {"STATUS": "IN_PROGRESS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []):
            payload = self.module.status()
        autonomy = payload.get("admin_autonomy", {})
        self.assertIsInstance(autonomy, dict)
        self.assertTrue(autonomy.get("active"))
        self.assertEqual(autonomy.get("trigger"), "stalled_lane")
        self.assertEqual(autonomy.get("target_role"), "dev")
        self.assertIn("streak_by_role", autonomy)

    def test_runtime_diagnostics_emits_admin_autonomy_findings(self) -> None:
        with mock.patch.object(self.module, "status", wraps=self.module.status):
            payload = self.module.runtime_diagnostics()
        findings = payload.get("top_findings", [])
        ids = {str(item.get("id")) for item in findings if isinstance(item, dict)}
        self.assertIn("ADMIN_STALL_TAKEOVER_ACTIVE", ids)
        signals = payload.get("signals", {})
        self.assertTrue(signals.get("admin_autonomy_active"))
        self.assertEqual(signals.get("admin_autonomy_trigger"), "stalled_lane")


if __name__ == "__main__":
    unittest.main()
