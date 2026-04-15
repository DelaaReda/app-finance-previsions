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
        f"fc_monitor_server_lite_health_semantics_{id(workspace)}", SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


class MonitorStatusLiteHealthSemanticsTests(unittest.TestCase):
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

    def test_lite_status_keeps_stale_runtime_health_when_primary_status_is_ok(self) -> None:
        contracts = {
            "planner": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            "dev": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            "admin": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
        }
        latest_snapshot = {
            "roles": {},
            "velocity": {},
            "summary": {"stale_context_open": 1, "blocker_roles": []},
            "health_snapshot": {"health": "STALE"},
            "critical_widget_health": {"state": "stale"},
        }

        def _fake_status_service(root: Path, status_builder, *, include_layers: bool = True):
            payload = status_builder()
            payload["primary_status"] = "ok"
            payload["doctor_overall_status"] = "ok"
            payload["layers"] = {"service": "status_service.v3", "mode": "lite", "collectors_omitted": True}
            return payload

        self.module._STATUS_LITE_CACHE["payload"] = None
        self.module._STATUS_LITE_CACHE["expires_at"] = 0.0
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(
            self.module, "_runtime_state_snapshot", lambda: {"execution_mode": "parallel_roles"}
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: latest_snapshot
        ), mock.patch.object(self.module, "rate_limits", lambda: []), mock.patch(
            "apps.monitor.services.status_service.build_status_snapshot", _fake_status_service
        ):
            payload = self.module.status(lite=1)

        self.assertEqual(payload.get("primary_status"), "ok")
        self.assertEqual(payload.get("doctor_overall_status"), "ok")
        self.assertEqual(payload.get("health"), "STALE")

    def test_lite_status_ignores_stale_summary_flags_when_current_agent_truth_is_clean(self) -> None:
        contracts = {
            "planner": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            "dev": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            "admin": {"STATUS": "PASS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
        }
        latest_snapshot = {
            "roles": {},
            "velocity": {},
            "summary": {
                "stale_context_open": 2,
                "stale_context_roles": ["admin", "scrum_master"],
                "blocker_roles": ["planner"],
            },
            "health_snapshot": {"health": "DEGRADED"},
            "critical_widget_health": {"state": "ok"},
        }

        def _fake_status_service(root: Path, status_builder, *, include_layers: bool = True):
            payload = status_builder()
            payload["primary_status"] = "ok"
            payload["doctor_overall_status"] = "ok"
            payload["layers"] = {"service": "status_service.v3", "mode": "lite", "collectors_omitted": True}
            return payload

        self.module._STATUS_LITE_CACHE["payload"] = None
        self.module._STATUS_LITE_CACHE["expires_at"] = 0.0
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(
            self.module, "_runtime_state_snapshot", lambda: {"execution_mode": "planner_experimental"}
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: latest_snapshot
        ), mock.patch.object(self.module, "rate_limits", lambda: []), mock.patch(
            "apps.monitor.services.status_service.build_status_snapshot", _fake_status_service
        ):
            payload = self.module.status(lite=1)

        self.assertEqual(payload.get("primary_status"), "ok")
        self.assertEqual(payload.get("doctor_overall_status"), "ok")
        self.assertEqual(payload.get("health"), "OK")


if __name__ == "__main__":
    unittest.main()
