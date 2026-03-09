from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "planner_dispatch_metrics.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_dispatch_metrics", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_dispatch_metrics"] = MODULE
SPEC.loader.exec_module(MODULE)


build_planner_dispatch_metrics = MODULE.build_planner_dispatch_metrics


class PlannerDispatchMetricsTests(unittest.TestCase):
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
