from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_DIR = ROOT / "platform" / "automation"
MONITOR_SRC_DIR = ROOT / "apps" / "monitor" / "src"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))
if str(MONITOR_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(MONITOR_SRC_DIR))

from runtime.core.contracts import CapabilityResult, CapabilityTask, DeliveryProof, OrchestrationEvent, PlannerGraphState, RuntimeCheck
from runtime.truth.event_store import EventStore
from runtime.planner.planner_graph_runtime import PlannerGraphRuntime
from runtime.planner.planner_dispatch_metrics import build_planner_dispatch_metrics


class OrchestrationRuntimeShadowTests(unittest.TestCase):
    def test_event_store_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = EventStore(root)
            store.append_event(
                OrchestrationEvent(
                    event_id="evt-1",
                    ts="2026-03-13T10:00:00Z",
                    event_type="graph.dispatch_capability",
                    cycle_id="cycle-1",
                    batch_id="BATCH-1",
                    task_id="BATCH-1-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    checkpoint_id="cp-1",
                    graph_node="dispatch_capability",
                    payload={"status": "running"},
                )
            )
            store.upsert_graph_state(
                PlannerGraphState(
                    cycle_id="cycle-1",
                    batch_id="BATCH-1",
                    task_id="BATCH-1-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    status="running",
                    current_node="wait_or_collect_result",
                    checkpoint_id="cp-1",
                    updated_at="2026-03-13T10:00:00Z",
                )
            )
            self.assertEqual(len(store.recent_events(hours=12, limit=10)), 1)
            states = store.latest_graph_states(limit=10)
            self.assertEqual(len(states), 1)
            self.assertEqual(states[0]["task_id"], "BATCH-1-DEV-01")

    def test_graph_runtime_observes_dispatch_result_merge(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime = PlannerGraphRuntime(root)
            task = CapabilityTask(
                cycle_id="cycle-1",
                batch_id="BATCH-1",
                task_id="BATCH-1-DEV-01",
                owner_role="planner",
                target_role="dev",
                task_kind="delivery",
                backend="codex_exec",
                model="gpt-5.3-codex-spark",
                thinking="low",
                sandbox="workspace-write",
                timeout_seconds=120,
                prompt_digest="abc123",
                prompt_preview="Do the thing",
            )
            runtime.observe_dispatch(task)
            runtime.observe_result(
                task,
                CapabilityResult(
                    cycle_id="cycle-1",
                    batch_id="BATCH-1",
                    task_id="BATCH-1-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    backend="codex_exec",
                    status="completed",
                    rc=0,
                    summary="Delivered",
                    blocking_issue="none",
                    artifact="evidence/proof.json",
                    verify="before=a; after=b; test=c",
                    files_touched="file.py",
                    tests_run="pytest -q",
                    commit_sha="abc",
                ),
                DeliveryProof(
                    cycle_id="cycle-1",
                    batch_id="BATCH-1",
                    task_id="BATCH-1-DEV-01",
                    artifact="evidence/proof.json",
                    verify="before=a; after=b; test=c",
                    tests_run="pytest -q",
                    commit_sha="abc",
                ),
                RuntimeCheck(
                    cycle_id="cycle-1",
                    task_id="BATCH-1-DEV-01",
                    status="ok",
                    source="unit-test",
                    detail={"proof": "present"},
                ),
            )
            state = runtime.observe_merge(task, True, note="merged")
            self.assertEqual(state["status"], "merged")
            self.assertEqual(runtime.snapshot(limit=10)["states"][0]["status"], "merged")

    def test_planner_dispatch_metrics_uses_shadow_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs_dir = root / "docs" / "operations" / "orchestrator"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "updated_at": "2026-03-13T10:00:00Z",
                        "items": [
                            {"id": "BATCH-1-DEV-01", "status": "READY_DEV", "owner": "dev"},
                            {"id": "BATCH-2-PLAN", "status": "READY_PLANNER", "owner": "planner"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (docs_dir / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "updated_at": "2026-03-13T10:00:00Z",
                        "tasks": [
                            {"task_id": "BATCH-1-DEV-01", "state": "READY_DEV", "role": "dev"},
                            {"task_id": "BATCH-2-PLAN", "state": "IN_PROGRESS", "role": "planner"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            runtime = PlannerGraphRuntime(root)
            runtime.observe_dispatch(
                CapabilityTask(
                    cycle_id="cycle-1",
                    batch_id="BATCH-1",
                    task_id="BATCH-1-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    task_kind="delivery",
                    backend="codex_exec",
                    model="gpt-5.3-codex-spark",
                    thinking="low",
                    sandbox="workspace-write",
                    timeout_seconds=120,
                    prompt_digest="abc123",
                    prompt_preview="Do the thing",
                )
            )
            metrics = build_planner_dispatch_metrics(root, recent_limit=12)
            self.assertEqual(metrics["ready_dev_count"], 1)
            self.assertEqual(metrics["ready_planner_count"], 1)
            self.assertEqual(metrics["planner_graph_state_count"], 1)
            self.assertIn(metrics["status"], {"ok", "degraded"})


if __name__ == "__main__":
    unittest.main()
