from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from runtime.core.contracts import PlannerGraphState
from runtime.truth.event_store import EventStore


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "runtime" / "planner" / "planner_board_runtime.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_board_runtime", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_board_runtime"] = MODULE
SPEC.loader.exec_module(MODULE)


snapshot = MODULE.snapshot


class PlannerBoardRuntimeTests(unittest.TestCase):
    def test_snapshot_ignores_historical_runtime_rows_for_active_subagent_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (root / "docs" / "product" / "planning").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "product" / "planning" / "CURRENT_EXECUTION_FOCUS_2026-03-13.md").write_text(
                "# active\n",
                encoding="utf-8",
            )
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "cycle_id": "2026-03-13-batch-24-alerting-intelligence-v2",
                            "doc_ref": "docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-13.md",
                            "dispatch_namespace": "BATCH",
                            "active_batch_ids": ["BATCH-85"],
                            "recent_completed_batch_ids": ["BATCH-84"],
                        },
                        "items": [
                            {
                                "id": "BATCH-85",
                                "batch_id": "BATCH-85",
                                "state": "IN_PROGRESS",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "cycle_id": "2026-03-13-batch-24-alerting-intelligence-v2",
                            "doc_ref": "docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-13.md",
                            "dispatch_namespace": "BATCH",
                            "active_batch_ids": ["BATCH-85"],
                            "recent_completed_batch_ids": ["BATCH-84"],
                        },
                        "tasks": [
                            {
                                "id": "BATCH-85-ANALYSIS",
                                "stream_id": "BATCH-85",
                                "role": "planner",
                                "state": "DONE",
                                "completed_at": "2026-04-15T04:13:51Z",
                            },
                            {
                                "id": "BATCH-85-ARCH",
                                "stream_id": "BATCH-85",
                                "role": "planner",
                                "state": "IN_PROGRESS",
                                "depends_on": ["BATCH-85-ANALYSIS"],
                            },
                            {
                                "id": "BATCH-85-DEV-01",
                                "stream_id": "BATCH-85",
                                "role": "dev",
                                "state": "WAITING_DEP",
                                "depends_on": ["BATCH-85-ARCH"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-83",
                    task_id="BATCH-83-ANALYSIS",
                    task_kind="analysis",
                    owner_role="planner",
                    target_role="dev",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-03-24T06:50:44Z",
                    engine="langgraph",
                    capability_request={
                        "task_id": "BATCH-83-ANALYSIS",
                        "target_role": "dev",
                        "metadata": {"subagent_id": "planner_dev_ghost"},
                    },
                    capability_result={"status": "running", "backend": "codex_exec", "summary": ""},
                )
            )
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-84",
                    task_id="BATCH-84-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="apply_workboard_mutation",
                    updated_at="2026-03-24T08:21:23Z",
                    engine="langgraph",
                    capability_request={
                        "task_id": "BATCH-84-DEV-01",
                        "target_role": "dev",
                        "metadata": {"subagent_id": "planner_dev_done"},
                    },
                    capability_result={"status": "completed", "backend": "codex_exec", "summary": "done"},
                )
            )

            snap = snapshot(root)

            self.assertEqual(snap["active_subagent_ids"], [])
            self.assertEqual(snap["active_subagents_count"], 0)
            self.assertFalse(snap["subagent_collect_pending_runtime"])
            self.assertFalse(snap["subagent_collect_pending"])
            self.assertEqual(snap["active_planner_task"]["task_id"], "BATCH-85-ARCH")
            self.assertEqual(snap["next_action"], "advance batch-85-arch")


if __name__ == "__main__":
    unittest.main()
