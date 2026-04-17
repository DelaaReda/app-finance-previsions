from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from runtime.core.contracts import CapabilityResult, CapabilityTask
from runtime.planner.planner_graph_runtime import PlannerGraphRuntime


class PlannerGraphRuntimeTests(unittest.TestCase):
    def test_observe_dispatch_clears_previous_result_on_redispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runtime = PlannerGraphRuntime(root)

            first_task = CapabilityTask(
                batch_id="BATCH-86",
                task_id="BATCH-86-DEV-02",
                owner_role="planner",
                target_role="dev",
                task_kind="delivery",
                metadata={"subagent_id": "planner_dev_old"},
            )
            failed_result = CapabilityResult(
                batch_id="BATCH-86",
                task_id="BATCH-86-DEV-02",
                owner_role="planner",
                target_role="dev",
                backend="codex_exec",
                status="failed",
                rc=1,
                summary="old failure",
                blocking_issue="invalid_subagent_result:start_banner_only",
                metadata={"subagent_id": "planner_dev_old"},
            )
            runtime.observe_dispatch(first_task)
            runtime.observe_result(first_task, failed_result)

            second_task = CapabilityTask(
                batch_id="BATCH-86",
                task_id="BATCH-86-DEV-02",
                owner_role="planner",
                target_role="dev",
                task_kind="delivery",
                metadata={"subagent_id": "planner_dev_new"},
            )
            snapshot = runtime.observe_dispatch(second_task)

            self.assertEqual(snapshot["status"], "running")
            self.assertEqual(snapshot["current_node"], "wait_or_collect_result")
            self.assertEqual(snapshot["blocking_issue"], "none")
            self.assertEqual(snapshot["capability_result"], {})
            self.assertEqual(snapshot["delivery_proof"], {})
            self.assertEqual(snapshot["guard_status"], "unknown")
            self.assertEqual(snapshot["runtime_health"], "unknown")
            self.assertEqual(snapshot["capability_request"]["metadata"]["subagent_id"], "planner_dev_new")

            # Re-read through the public store API to ensure SQLite no longer keeps the old result.
            stored = runtime.store.load_graph_state("BATCH-86-DEV-02")
            self.assertEqual(stored.get("capability_result"), {})
            self.assertEqual(stored.get("delivery_proof"), {})
            self.assertEqual(
                ((stored.get("capability_request") or {}).get("metadata") or {}).get("subagent_id"),
                "planner_dev_new",
            )
