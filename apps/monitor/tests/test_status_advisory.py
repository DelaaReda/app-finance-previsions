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
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_status_advisory_{id(workspace)}", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


class MonitorStatusAdvisoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
        (self.root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl").write_text("", encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)
        self.module = _load_server_module(self.root, self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_includes_advisory_and_message_bus_counters(self) -> None:
        contracts = {
            "planner": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "OK", "BLOCKER_ID": "NONE", "NEXT": "owner=planner; action=continue"},
            "dev": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "OK", "BLOCKER_ID": "NONE", "NEXT": "owner=dev; action=continue"},
            "admin": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "OK", "BLOCKER_ID": "NONE", "NEXT": "owner=admin; action=continue"},
            "scrum_master": {"STATUS": "BLOCKED", "VERDICT": "BLOCKED", "DELTA": "ADVISORY", "BLOCKER_ID": "TEST_ONLY", "NEXT": "owner=scrum_master; action=report"},
        }

        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 3 if role == "scrum_master" else 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []):
            payload = self.module.status()

        self.assertIn(payload.get("health"), {"STALE", "DEGRADED", "OK"})
        self.assertIn("po_scrum_master", payload)
        self.assertIsInstance(payload["po_scrum_master"], dict)
        self.assertEqual(payload["po_scrum_master"].get("name"), "po_scrum_master")
        self.assertIn(payload["po_scrum_master"].get("mode"), {"disabled_compat", "scheduled_advisory"})
        if payload["po_scrum_master"].get("mode") == "disabled_compat":
            self.assertFalse(payload["po_scrum_master"].get("active"))
        self.assertIn("lock_skip_streak", payload["po_scrum_master"])
        self.assertIn("tick_tail", payload["po_scrum_master"])
        self.assertIn("runner_tail", payload["po_scrum_master"])
        self.assertIn("events_tail", payload["po_scrum_master"])
        self.assertIn("agent_messages", payload)
        self.assertIsInstance(payload["agent_messages"], dict)
        for field in ("open", "open_count", "delivered", "delivered_count", "actioned", "actioned_count", "closed", "closed_count"):
            self.assertIn(field, payload["agent_messages"])

    def test_log_catalog_exposes_scrum_master_when_logs_exist(self) -> None:
        (self.root / "logs-codex-runs" / "fc-ticks" / "scrum_master.tick.log").write_text(
            "2026-03-04T10:00:00 [END] role=scrum_master rc=0\n",
            encoding="utf-8",
        )
        (self.root / "logs-codex-runs" / "role-runner" / "scrum_master.live.log").write_text(
            "2026-03-04T10:00:00Z role=scrum_master event=final_output detail=ok\n",
            encoding="utf-8",
        )
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")):
            payload = self.module.log_catalog()
        self.assertIn("scrum_master", payload.get("roles", []))
        catalog = payload.get("catalog", {}).get("scrum_master", {})
        self.assertTrue(catalog.get("tick", {}).get("exists"))
        self.assertTrue(catalog.get("runner", {}).get("exists"))

    def test_stale_non_core_contract_is_hidden_in_planner_mode(self) -> None:
        dev_contract = self.state / "dev.last_contract"
        dev_contract.write_text(
            "\n".join([
                "STATUS: BLOCKED",
                "DELTA: CONTRACT_GUARD_BLOCK",
                "EVIDENCE: task_update=blocked",
                "RISKS: invalid arch check",
                "NEXT: owner=dev; action=fix",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: DEV_ARCH_CHECK_FORMAT_INVALID",
                "NEXT_ACTION_UNIQUE: DEV_FIX",
            ]),
            encoding="utf-8",
        )
        old_epoch = 1772800000 - 7200
        os.utime(dev_contract, (old_epoch, old_epoch))
        with mock.patch.dict(
            os.environ,
            {
                "FC_PLANNER_ORCHESTRATOR_ENABLED": "1",
                "FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY": "1",
            },
            clear=False,
        ), mock.patch.object(self.module, "_active_planner_subagent_roles", lambda: ()), mock.patch.object(
            self.module.time, "time", lambda: 1772800000
        ):
            self.assertEqual(self.module.contract("dev"), {})
            self.assertEqual(self.module.contract_raw("dev"), "")

    def test_stale_admin_takeover_state_is_hidden_in_planner_mode(self) -> None:
        (self.state / "admin.tshape.state.json").write_text(
            json.dumps(
                {
                    "active": True,
                    "target_role": "dev",
                    "since_ts": "2026-03-06T10:00:00Z",
                    "reason_blocker": "DEV_ARCH_CHECK_FORMAT_INVALID",
                    "last_action": "takeover_preflight_ok",
                    "resolved": False,
                    "blocked_roles": ["dev"],
                }
            ),
            encoding="utf-8",
        )
        (self.state / "admin_autonomy_state.json").write_text(
            json.dumps(
                {
                    "active": True,
                    "trigger": "blocked_explicit",
                    "target_role": "dev",
                    "target_task": "none",
                    "reason_blocker": "BLOCKED_RUNTIME",
                    "last_action": "takeover_active",
                    "last_outcome": "partial",
                    "since_ts": "2026-03-06T10:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.dict(
            os.environ,
            {
                "FC_PLANNER_ORCHESTRATOR_ENABLED": "1",
                "FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY": "1",
            },
            clear=False,
        ), mock.patch.object(self.module, "_active_planner_subagent_roles", lambda: ()), mock.patch.object(
            self.module.time, "time", lambda: 1772800000
        ):
            tshape = self.module.admin_tshape_snapshot()
            autonomy = self.module.admin_autonomy_snapshot()
        self.assertFalse(tshape.get("active"))
        self.assertEqual(tshape.get("reason_blocker"), "STALE_SUPPRESSED")
        self.assertFalse(autonomy.get("active"))
        self.assertEqual(autonomy.get("trigger"), "stale_suppressed")


if __name__ == "__main__":
    unittest.main()
