from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_ROOT = REPO_ROOT / "platform" / "automation"
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))

from runtime.core.contracts import OrchestrationEvent, PlannerGraphState
from runtime.truth.event_store import EventStore


SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"


def _load_server_module(workspace: Path, state_dir: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    os.environ["FC_MONITOR_STATE_DIR"] = str(state_dir)
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_event_store_{id(workspace)}", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed")
        raise
    return module


class MonitorStatusEventStoreFallbackTests(unittest.TestCase):
    def test_planner_subagents_snapshot_prefers_event_store_reader(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / "state"
            state.mkdir(parents=True, exist_ok=True)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )

            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(json.dumps({"items": [{"id": "BATCH-77", "state": "READY_DEV"}]}), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(
                json.dumps({"tasks": [{"id": "BATCH-77-DEV-01", "stream_id": "BATCH-77", "state": "IN_PROGRESS"}]}),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-77",
                    task_id="BATCH-77-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="apply_workboard_mutation",
                    updated_at="2026-03-13T12:00:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-77-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "pass",
                        "backend": "codex_exec",
                        "summary": "Capability completed successfully",
                        "artifact": "docs/operations/orchestrator/proofs/BATCH-77/proof.yaml",
                        "verify": "pytest -q",
                        "tests_run": "pytest -q",
                        "files_touched": "src/example.py",
                        "commit_sha": "def456",
                    },
                )
            )
            store.append_event(
                OrchestrationEvent(
                    event_id="event-77",
                    ts="2026-03-13T12:00:10Z",
                    event_type="graph.close_or_requeue",
                    batch_id="BATCH-77",
                    task_id="BATCH-77-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    checkpoint_id="chk-77",
                    graph_node="close_or_requeue",
                    payload={"status": "pass", "task_id": "BATCH-77-DEV-01"},
                )
            )

            server = _load_server_module(root, state)
            server._PLANNER_SUBAGENTS_CACHE["payload"] = None
            server._PLANNER_SUBAGENTS_CACHE["ts"] = 0.0

            with mock.patch.object(server, "monitor_latest_snapshot", lambda: {}):
                snapshot = server._planner_subagents_snapshot()

            self.assertEqual(snapshot.get("source"), "event_store")
            self.assertEqual(snapshot.get("recent_success_count"), 1)
            self.assertEqual(snapshot.get("planner_graph_state_count"), 1)
            self.assertEqual(snapshot.get("ready_dev_count"), 1)


if __name__ == "__main__":
    unittest.main()
