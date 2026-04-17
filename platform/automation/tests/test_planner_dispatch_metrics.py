from __future__ import annotations

import importlib.util
import json
import os
import subprocess
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

MODULE_PATH = AUTOMATION_DIR / "runtime" / "planner" / "planner_dispatch_metrics.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_dispatch_metrics", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_dispatch_metrics"] = MODULE
SPEC.loader.exec_module(MODULE)


build_planner_dispatch_metrics = MODULE.build_planner_dispatch_metrics


class PlannerDispatchMetricsTests(unittest.TestCase):
    def test_event_store_primary_ignores_historical_residue_without_open_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [{"id": "BATCH-89", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-89-DEV-03", "stream_id": "BATCH-89", "role": "dev", "state": "DONE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-89",
                    task_id="BATCH-89-DEV-03",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-04-15T16:43:55Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-89-DEV-03", "target_role": "dev"},
                    capability_result={"status": "pass", "backend": "codex_exec", "summary": "historical merge residue"},
                )
            )

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertTrue(metrics["event_store_primary"])
            self.assertEqual(metrics["active_count"], 0)
            self.assertEqual(len(metrics.get("recent", [])), 0)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["planner_state"], "idle")
            self.assertEqual(metrics["current_bottleneck"], "none")
            self.assertEqual(metrics["recommended_next_action"], "monitor")
            self.assertFalse(metrics["historical_runtime_residue_detected"])

    def test_done_owner_task_quarantines_historical_ready_to_merge_residue_with_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [{"id": "BATCH-90", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-90-ADMIN-01", "stream_id": "BATCH-90", "role": "admin", "state": "DONE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-90",
                    task_id="BATCH-90-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="ready_to_merge",
                    current_node="apply_workboard_mutation",
                    updated_at="2026-04-15T19:08:09Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-90-ADMIN-01", "target_role": "admin"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "Runtime unblock verified.",
                        "artifact": "commit=d87d334f",
                        "verify": "pytest -q target",
                        "tests_run": "pytest -q target",
                        "commit_sha": "d87d334f",
                    },
                )
            )

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertTrue(metrics["event_store_primary"])
            self.assertEqual(metrics["active_count"], 0)
            self.assertEqual(metrics["quarantined_retryable_residue_count"], 1)
            self.assertFalse(metrics["historical_runtime_residue_detected"])
            self.assertEqual(metrics["current_bottleneck"], "none")
            self.assertEqual(metrics["recommended_next_action"], "monitor")

    def test_claim_cli_reconciles_queue_state_with_planner_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "BATCH-70",
                                "state": "READY_PLANNER",
                                "dispatch_authorized": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "streams": [{"id": "BATCH-70", "state": "READY_PLANNER"}],
                        "tasks": [
                            {
                                "id": "BATCH-70-GOV_REVIEW",
                                "stream_id": "BATCH-70",
                                "role": "planner",
                                "state": "READY_PLANNER",
                                "depends_on": ["BATCH-70-ADMIN-01"],
                            },
                            {
                                "id": "BATCH-70-ADMIN-01",
                                "stream_id": "BATCH-70",
                                "role": "admin",
                                "state": "DONE",
                                "depends_on": [],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            automation_pythonpath = str(AUTOMATION_DIR)
            existing_pythonpath = str(env.get("PYTHONPATH", "") or "").strip()
            env["PYTHONPATH"] = (
                automation_pythonpath
                if not existing_pythonpath
                else automation_pythonpath + os.pathsep + existing_pythonpath
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(AUTOMATION_DIR / "runtime" / "planner" / "planner_runtime_actions.py"),
                    "--root",
                    str(root),
                    "claim",
                    "--role",
                    "planner",
                    "--task",
                    "BATCH-70-GOV_REVIEW",
                ],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            queue = json.loads((orch / "priority-queue.json").read_text(encoding="utf-8"))
            self.assertEqual(queue["items"][0]["state"], "IN_PROGRESS")

    def test_event_store_primary_quarantines_active_row_conflicting_with_workboard_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "BATCH-70-DEV-01",
                                "owner": "dev",
                                "status": "READY_DEV",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-70-ANALYSIS",
                                "stream_id": "BATCH-70",
                                "role": "planner",
                                "state": "DONE",
                            },
                            {
                                "id": "BATCH-70-DEV-01",
                                "stream_id": "BATCH-70",
                                "role": "dev",
                                "state": "READY_DEV",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-70",
                    task_id="BATCH-70-ANALYSIS",
                    task_kind="analysis",
                    owner_role="planner",
                    target_role="dev",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-03-20T14:10:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-70-ANALYSIS", "target_role": "dev"},
                    capability_result={"status": "running", "backend": "codex_exec", "summary": ""},
                )
            )

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertTrue(metrics["event_store_primary"])
            self.assertFalse(metrics["projection_secondary_only"])
            self.assertEqual(metrics["active_count"], 0)
            self.assertEqual(metrics["runtime_inconsistent_active_count"], 1)
            self.assertEqual(metrics["ready_dev_count"], 1)
            self.assertEqual(metrics["status"], "dispatch_needed")

    def test_event_store_primary_uses_workboard_ready_planner_when_queue_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-63-ADMIN-01",
                                "stream_id": "BATCH-63",
                                "role": "planner",
                                "state": "READY_PLANNER",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-62",
                    task_id="BATCH-62-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-03-13T12:00:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-62-DEV-01", "target_role": "dev"},
                    capability_result={"status": "pass", "backend": "codex_exec", "summary": "done"},
                )
            )

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertTrue(metrics["event_store_primary"])
            self.assertEqual(metrics["runtime_truth_source"], "sqlite")
            self.assertEqual(metrics["status"], "dispatch_needed")
            self.assertEqual(metrics["ready_total"], 1)
            self.assertEqual(metrics["ready_planner_count"], 1)
            self.assertEqual(metrics["planner_state"], "idle")

    def test_event_store_primary_filters_recent_history_to_active_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-85"]},
                        "items": [
                            {
                                "id": "BATCH-85",
                                "state": "WAITING_DEP",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-85"]},
                        "tasks": [
                            {
                                "id": "BATCH-85-ANALYSIS",
                                "stream_id": "BATCH-85",
                                "role": "planner",
                                "state": "IN_PROGRESS",
                            },
                            {
                                "id": "BATCH-85-PLAN",
                                "stream_id": "BATCH-85",
                                "role": "planner",
                                "state": "READY_PLANNER",
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
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-03-13T12:00:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-83-ANALYSIS", "target_role": "dev"},
                    capability_result={"status": "pass", "backend": "codex_exec", "summary": "done"},
                )
            )

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertTrue(metrics["event_store_primary"])
            self.assertEqual(metrics["recent_total"], 0)
            self.assertEqual(metrics["latest_owner_task_id"], "")
            self.assertEqual(metrics["tasks_progressed_last_1h"], 0)
            self.assertEqual(metrics["ready_planner_count"], 1)
            self.assertEqual(metrics["status"], "dispatch_needed")

    def test_done_owner_task_quarantines_retryable_residue_without_invalid_result_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-87"]},
                        "items": [{"id": "BATCH-87", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-87"]},
                        "tasks": [
                            {"id": "BATCH-87-ADMIN-01", "stream_id": "BATCH-87", "role": "admin", "state": "DONE"},
                            {
                                "id": "BATCH-87-GOV_REVIEW",
                                "stream_id": "BATCH-87",
                                "role": "planner",
                                "state": "IN_PROGRESS",
                                "depends_on": ["BATCH-87-ADMIN-01"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-87",
                    task_id="BATCH-87-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="retryable",
                    current_node="close_or_requeue",
                    updated_at="2026-04-15T11:18:36Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-87-ADMIN-01", "target_role": "admin"},
                    capability_result={
                        "status": "failed",
                        "backend": "codex_exec",
                        "summary": "Cannot continue with precise SQLite-based runtime audit yet because query command failed; retrying with corrected quoting.",
                        "blocking_issue": "SQL quoting error.",
                        "artifact": "None.",
                        "verify": "None.",
                        "tests_run": "None.",
                        "commit_sha": "none",
                    },
                )
            )

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertTrue(metrics["event_store_primary"])
            self.assertEqual(metrics["quarantined_retryable_residue_count"], 1)
            self.assertEqual(metrics["active_count"], 0)
            self.assertEqual(metrics["status"], "ok")

    def test_build_planner_dispatch_metrics_counts_success_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            results = orch / "planner-subagents-results"
            results.mkdir(parents=True, exist_ok=True)
            registry = {
                "subagents": [
                    {
                        "subagent_id": "planner_dev_ok",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-1-DEV-01",
                        "status": "completed",
                        "summary": "ok",
                        "artifact": "artifact.txt",
                        "last_update_at": "2026-03-07T06:00:00Z",
                    },
                    {
                        "subagent_id": "planner_admin_fail",
                        "target_role": "admin",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-2-ADMIN-01",
                        "status": "failed",
                        "summary": "failed",
                        "artifact": "artifact.txt",
                        "last_update_at": "2026-03-07T06:01:00Z",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            (results / "planner_dev_ok.raw.txt").write_text("normal success", encoding="utf-8")
            (results / "planner_admin_fail.raw.txt").write_text("Gateway agent failed; falling back to embedded", encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["recent_total"], 2)
            self.assertEqual(metrics["recent_success_count"], 1)
            self.assertEqual(metrics["recent_failed_count"], 1)
            self.assertEqual(metrics["recent_fallback_like_count"], 1)
            self.assertEqual(metrics["latest_status"], "failed")
            self.assertTrue(metrics["latest_fallback_like"])
            self.assertEqual(metrics["status"], "degraded")

    def test_latest_clean_success_clears_dispatch_degraded_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            results = orch / "planner-subagents-results"
            results.mkdir(parents=True, exist_ok=True)
            registry = {
                "subagents": [
                    {
                        "subagent_id": "planner_dev_fail",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-1-DEV-01",
                        "status": "merged",
                        "summary": "fallback merged",
                        "artifact": "none",
                        "last_update_at": "2026-03-07T06:00:00Z",
                    },
                    {
                        "subagent_id": "planner_dev_ok",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-2-DEV-01",
                        "status": "completed",
                        "summary": "clean success",
                        "artifact": "artifact.txt",
                        "last_update_at": "2026-03-07T06:05:00Z",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            (results / "planner_dev_fail.raw.txt").write_text("Gateway agent failed; falling back to embedded", encoding="utf-8")
            (results / "planner_dev_ok.raw.txt").write_text("clean success", encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["recent_fallback_like_count"], 1)
            self.assertEqual(metrics["latest_status"], "completed")
            self.assertFalse(metrics["latest_fallback_like"])
            self.assertEqual(metrics["latest_owner_task_id"], "BATCH-2-DEV-01")
            self.assertEqual(metrics["status"], "ok")

    def test_active_subagent_keeps_dispatch_ok_despite_recent_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            results = orch / "planner-subagents-results"
            results.mkdir(parents=True, exist_ok=True)
            registry = {
                "subagents": [
                    {
                        "subagent_id": "planner_dev_fail",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-1-DEV-01",
                        "status": "failed",
                        "summary": "fallback failed",
                        "artifact": "none",
                        "last_update_at": "2026-03-07T06:00:00Z",
                    },
                    {
                        "subagent_id": "planner_dev_active",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-2-DEV-01",
                        "status": "running",
                        "summary": "",
                        "artifact": "",
                        "last_update_at": "2026-03-07T06:05:00Z",
                        "created_at": "2026-03-07T06:05:00Z",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            (results / "planner_dev_fail.raw.txt").write_text("Gateway agent failed; falling back to embedded", encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["active_count"], 1)
            self.assertEqual(metrics["recent_failed_count"], 1)
            self.assertEqual(metrics["recent_fallback_like_count"], 1)
            self.assertEqual(metrics["status"], "ok")

    def test_metrics_surface_recovering_invalid_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            results = orch / "planner-subagents-results"
            results.mkdir(parents=True, exist_ok=True)
            registry = {
                "subagents": [
                    {
                        "subagent_id": "planner_admin_invalid",
                        "target_role": "admin",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-9-ADMIN-01",
                        "status": "failed",
                        "summary": "worker quit with fatal: Transport channel closed",
                        "artifact": "",
                        "blocking_issue": "subagent_invalid_result:start_banner_only",
                        "last_update_at": "2026-03-07T06:00:00Z",
                    },
                    {
                        "subagent_id": "planner_dev_active",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-10-DEV-01",
                        "status": "running",
                        "summary": "",
                        "artifact": "",
                        "last_update_at": "2026-03-07T06:05:00Z",
                        "created_at": "2026-03-07T06:05:00Z",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["active_count"], 1)
            self.assertEqual(metrics["recent_invalid_result_count"], 1)
            self.assertTrue(metrics["recovering"])
            self.assertEqual(metrics["latest_failure_mode"], "invalid_result")
            self.assertEqual(metrics["status"], "ok")

    def test_metrics_surface_long_running_and_no_progress_dev_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            results = orch / "planner-subagents-results"
            results.mkdir(parents=True, exist_ok=True)
            registry = {
                "subagents": [
                    {
                        "subagent_id": "planner_dev_active",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-12-DEV-03",
                        "status": "running",
                        "summary": "",
                        "artifact": "",
                        "last_update_at": "2026-03-07T06:05:00Z",
                        "created_at": "2026-03-07T06:05:00Z",
                    },
                ]
            }
            workboard = {
                "tasks": [
                    {
                        "id": "BATCH-12-DEV-03",
                        "role": "dev",
                        "state": "IN_PROGRESS",
                        "dev_execution_state": "long_running",
                    },
                    {
                        "id": "BATCH-61-DEV-01",
                        "role": "dev",
                        "state": "IN_PROGRESS",
                        "dev_execution_state": "no_progress",
                        "dev_no_progress_streak": 1,
                        "dev_recovery_required": True,
                        "stalled_capability_reason": "dev_no_progress_streak:1",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(json.dumps(workboard), encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["long_running_dev_count"], 1)
            self.assertEqual(metrics["dev_no_progress_count"], 1)
            self.assertEqual(metrics["recovery_required_count"], 1)
            self.assertTrue(metrics["recovering"])

    def test_metrics_ignore_done_dev_runtime_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            registry = {"subagents": []}
            workboard = {
                "tasks": [
                    {
                        "id": "BATCH-12-DEV-03",
                        "role": "dev",
                        "state": "DONE",
                        "dev_execution_state": "orphaned",
                        "dev_orphaned_streak": 3,
                    },
                    {
                        "id": "BATCH-61-DEV-02",
                        "role": "dev",
                        "state": "IN_PROGRESS",
                        "dev_execution_state": "running",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(json.dumps(workboard), encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["dev_orphaned_count"], 0)
            self.assertEqual(metrics["long_running_dev_count"], 0)
            self.assertEqual(metrics["dev_no_progress_count"], 0)


if __name__ == "__main__":
    unittest.main()
