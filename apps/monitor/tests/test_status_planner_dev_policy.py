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
        f"fc_monitor_server_planner_dev_policy_{id(workspace)}", SERVER_PATH
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


class MonitorStatusPlannerDevPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)

        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(
            json.dumps({"items": [{"id": "BATCH-10", "state": "READY"}]}), encoding="utf-8"
        )
        (orch / "parallel-workstreams.json").write_text(
            json.dumps({"tasks": []}), encoding="utf-8"
        )
        (orch / "agent-iteration-issues.jsonl").write_text("", encoding="utf-8")

        (self.root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl").write_text("", encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)

        (self.state / "planner_autonomy_state.json").write_text(
            json.dumps(
                {
                    "active": True,
                    "since_ts": "2026-03-05T18:00:00Z",
                    "last_action": "create_and_claim",
                    "last_outcome": "resolved",
                    "policy_enforced": True,
                    "wait_forbidden": True,
                },
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )
        self.module = _load_server_module(self.root, self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_exposes_planner_and_dev_policy_fields(self) -> None:
        contracts = {
            "planner": {
                "STATUS": "WAIT",
                "VERDICT": "PASS",
                "DELTA": "NO_DELTA",
                "BLOCKER_ID": "NONE",
                "EVIDENCE": "task_update=none_no_signal; issues=planner_passivity_corrected",
            },
            "dev": {
                "STATUS": "WAIT",
                "VERDICT": "PASS",
                "DELTA": "DEV_WAIT_NO_READY_TASK",
                "BLOCKER_ID": "NONE",
                "EVIDENCE": "task_update=none_no_ready",
            },
            "admin": {
                "STATUS": "IN_PROGRESS",
                "VERDICT": "PASS",
                "DELTA": "NO_DELTA",
                "BLOCKER_ID": "NONE",
            },
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []):
            payload = self.module.status()

        self.assertTrue(payload.get("planner_policy_enforced"))
        self.assertEqual(payload.get("planner_autonomy_last_action"), "create_and_claim")
        self.assertEqual(payload.get("planner_autonomy_last_outcome"), "resolved")
        self.assertEqual(payload.get("dev_wait_reason"), "no_dev_ready_task")

        planner = payload.get("agents", {}).get("planner", {})
        self.assertEqual(planner.get("status"), "IN_PROGRESS")
        self.assertEqual(planner.get("delta"), "PLANNER_AUTONOMY_ENFORCED")

        dev = payload.get("agents", {}).get("dev", {})
        self.assertEqual(dev.get("dev_wait_reason"), "no_dev_ready_task")

    def test_runtime_diagnostics_emits_policy_findings(self) -> None:
        status_snapshot = {
            "health": "OK",
            "data_freshness_s": 30,
            "data_source": "runtime_logs",
            "planner_policy_enforced": True,
            "planner_autonomy_last_action": "create_and_claim",
            "planner_autonomy_last_outcome": "resolved",
            "dev_wait_reason": "no_dev_ready_task",
            "agents": {
                "planner": {"status": "IN_PROGRESS", "verdict": "GO_WITH_CAUTION", "delta": "PLANNER_AUTONOMY_ENFORCED", "blocker": "NONE"},
                "dev": {"status": "WAIT", "verdict": "PASS", "delta": "DEV_WAIT_NO_READY_TASK", "blocker": "NONE"},
                "admin": {"status": "IN_PROGRESS", "verdict": "PASS", "delta": "NO_DELTA", "blocker": "NONE"},
            },
            "issue_publication_gap_roles": [],
            "dev_parent": {},
            "dispatcher_tshape": {},
            "admin_autonomy": {"active": False, "needs_human_review_by_role": {"planner": False, "dev": False}},
            "queue": {"state_counts": {"READY": 0, "WAITING_DEP": 0, "IN_PROGRESS": 0}},
            "po_scrum_master": {},
            "agent_messages": {},
        }
        with mock.patch.object(self.module, "status", lambda: status_snapshot), mock.patch.object(
            self.module, "contract", lambda role: {"EVIDENCE": "issues=planner_passivity_corrected"} if role == "planner" else {}
        ):
            payload = self.module.runtime_diagnostics()

        findings = payload.get("top_findings", [])
        ids = {str(item.get("id")) for item in findings if isinstance(item, dict)}
        self.assertIn("PLANNER_PASSIVITY_VIOLATION_CORRECTED", ids)
        self.assertIn("DEV_WAIT_NO_READY_TASK", ids)
        self.assertIn("PLANNER_AUTONOMY_CREATE_CLAIM", ids)


if __name__ == "__main__":
    unittest.main()
