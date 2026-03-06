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
    os.environ["FC_MONITOR_ROLES"] = "planner,dev,admin,scrum_master"
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_core_health_{id(workspace)}", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


def _write_contract(state_dir: Path, role: str, *, status: str, verdict: str, blocker: str) -> None:
    payload = (
        f"STATUS: {status}\n"
        f"DELTA: TEST_DELTA\n"
        "EVIDENCE: run_note=core health test;\n"
        "RISKS: none\n"
        "NEXT: owner=test; action=continue\n"
        f"VERDICT: {verdict}\n"
        f"BLOCKER_ID: {blocker}\n"
        f"NEXT_ACTION_UNIQUE: TEST_{role.upper()}_T1\n"
    )
    (state_dir / f"{role}.last_contract").write_text(payload, encoding="utf-8")


class MonitorHealthCoreRolesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")

        logs = self.root / "logs-codex-runs" / "fc-ticks"
        logs.mkdir(parents=True, exist_ok=True)
        for role in ("planner", "dev", "admin", "scrum_master"):
            (logs / f"{role}.tick.log").write_text("tick\n", encoding="utf-8")

        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)
        _write_contract(self.state, "planner", status="IN_PROGRESS", verdict="GO", blocker="NONE")
        _write_contract(self.state, "dev", status="IN_PROGRESS", verdict="GO", blocker="NONE")
        _write_contract(self.state, "admin", status="IN_PROGRESS", verdict="GO", blocker="NONE")
        _write_contract(self.state, "scrum_master", status="BLOCKED", verdict="BLOCKED", blocker="ADVISORY_NOTE")

        self.module = _load_server_module(self.root)
        self._prev_state = self.module.STATE
        self.module.STATE = self.state

    def tearDown(self) -> None:
        self.module.STATE = self._prev_state
        self._tmp.cleanup()
        os.environ.pop("FC_MONITOR_ROLES", None)

    def test_health_ignores_advisory_blockers(self) -> None:
        payload = self.module.status()
        self.assertIn(payload.get("health"), {"DEGRADED", "STALE", "OK"})
        self.assertIn("scrum_master", payload.get("agents", {}))
        self.assertEqual(payload["agents"]["scrum_master"]["blocker"], "ADVISORY_NOTE")


if __name__ == "__main__":
    unittest.main()

