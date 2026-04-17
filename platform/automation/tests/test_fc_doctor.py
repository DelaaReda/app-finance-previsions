#!/usr/bin/env python3
from __future__ import annotations

import unittest
import importlib.util
import sys
import json
import tempfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
DOCTOR_PATH = ROOT / "platform" / "automation" / "fc_doctor.py"
_SPEC = importlib.util.spec_from_file_location("fc_doctor_local", DOCTOR_PATH)
assert _SPEC and _SPEC.loader
fc_doctor = importlib.util.module_from_spec(_SPEC)
sys.modules["fc_doctor_local"] = fc_doctor
_SPEC.loader.exec_module(fc_doctor)


class FCDoctorTests(unittest.TestCase):
    def tearDown(self) -> None:
        fc_doctor._load_product_priority_guard.cache_clear()
        fc_doctor._load_planner_dispatch_metrics.cache_clear()
        fc_doctor._build_delivery_control_metrics.cache_clear()
        fc_doctor._build_planner_dispatch_metrics.cache_clear()

    def test_capability_stall_recovery_treats_single_transient_timeout_as_ok(self) -> None:
        metrics = {
            "capability_stall_summary": {
                "count": 1,
                "items": [
                    {
                        "task_id": "BATCH-12-DEV-02",
                        "role": "dev",
                        "timeout_streak": 1,
                        "invalid_result_streak": 0,
                        "takeover_required": False,
                        "recovery_required": False,
                    }
                ],
            }
        }
        module = SimpleNamespace(build_delivery_control_metrics=lambda root, window_hours=24: metrics)
        with patch.object(fc_doctor, "_load_product_priority_guard", return_value=module):
            result = fc_doctor.check_capability_stall_recovery(ROOT)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("recovery_mode"), "transient_capability_requeue_active")

    def test_planner_takeover_recovery_treats_single_transient_timeout_as_ok(self) -> None:
        metrics = {
            "capability_stall_summary": {
                "count": 1,
                "items": [
                    {
                        "task_id": "BATCH-12-DEV-02",
                        "role": "dev",
                        "timeout_streak": 1,
                        "invalid_result_streak": 0,
                        "takeover_required": False,
                        "recovery_required": False,
                    }
                ],
            }
        }
        module = SimpleNamespace(build_delivery_control_metrics=lambda root, window_hours=24: metrics)
        with patch.object(fc_doctor, "_load_product_priority_guard", return_value=module):
            result = fc_doctor.check_planner_takeover_recovery(ROOT)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("recovery_mode"), "transient_capability_requeue_active")

    def test_state_equivalence_planned_waiting_dep(self) -> None:
        self.assertTrue(fc_doctor._states_equivalent("PLANNED", "WAITING_DEP"))
        self.assertTrue(fc_doctor._states_equivalent("CLOSED", "DONE"))
        self.assertFalse(fc_doctor._states_equivalent("READY", "WAITING_DEP"))

    def test_check_sessions_matches_role_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 0, "cron_planner_only": 0}}}),
                encoding="utf-8",
            )
            fake = SimpleNamespace(
                returncode=0,
                stdout="codex_planner_cron\ncodex_dev_cron\ncodex_admin_cron\n",
                stderr="",
            )
            with patch.dict(
                fc_doctor.os.environ,
                {
                    "FC_EXPERIMENTAL_PLANNER_ONLY": "0",
                    "FC_PLANNER_ORCHESTRATOR_ENABLED": "0",
                    "FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY": "0",
                },
                clear=False,
            ):
                with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                    result = fc_doctor.check_sessions(root)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("missing_core"), [])
        found = result.detail.get("found_core", {})
        self.assertIn("planner", found)
        self.assertIn("dev", found)
        self.assertIn("admin", found)

    def test_check_sessions_uses_planner_only_core_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )
            fake = SimpleNamespace(
                returncode=0,
                stdout="codex_planner_cron\n",
                stderr="",
            )
            with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                result = fc_doctor.check_sessions(root)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("expected_core"), ["planner"])
        self.assertEqual(result.detail.get("missing_core"), [])
        self.assertEqual(result.detail.get("execution_mode"), "planner_experimental")

    def test_check_sessions_reports_orphan_tmux_sessions_in_planner_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )
            fake = SimpleNamespace(
                returncode=0,
                stdout="codex_planner_cron\ncodex_scrum_master_cron\n",
                stderr="",
            )
            with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                result = fc_doctor.check_sessions(root)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("expected_core"), ["planner"])
        self.assertEqual(result.detail.get("orphans"), ["codex_scrum_master_cron"])

    def test_check_sessions_paused_runtime_suppresses_missing_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )
            runtime_state_dir = root / "logs-codex-runs" / "orchestrator-state"
            runtime_state_dir.mkdir(parents=True, exist_ok=True)
            (runtime_state_dir / "runtime-state.json").write_text(
                json.dumps({"lifecycle": "paused", "reason": "operator_paused_runtime"}),
                encoding="utf-8",
            )
            fake = SimpleNamespace(returncode=1, stdout="", stderr="no server running on /tmp/tmux-1000/default")
            with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                result = fc_doctor.check_sessions(root)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("missing_core"), [])
        self.assertEqual(result.detail.get("missing_core_raw"), ["planner"])

    def test_build_payload_has_expected_schema(self) -> None:
        payload, code = fc_doctor.build_payload(
            root=ROOT,
            api_base="http://127.0.0.1:1",
            monitor_base="http://127.0.0.1:1",
        )
        self.assertIn(code, (0, 1, 2))
        self.assertIsInstance(payload, dict)
        self.assertIn("status", payload)
        self.assertIn("checks", payload)
        self.assertIn("meta", payload)
        for key in ("workspace_root", "runtime_state", "scheduler_authority", "sessions", "locks", "queue_workboard", "providers", "product_value", "delivery_integrity", "delivery_future_integrity", "browser_proof_pipeline", "suspicious_completions", "qa_review_pipeline", "dev_execution_model", "dev_progress_integrity", "dev_orphan_recovery", "capability_result_integrity", "planner_takeover_recovery", "planner_dispatch"):
            self.assertIn(key, payload["checks"])
        queue_workboard = payload["checks"].get("queue_workboard", {})
        self.assertIsInstance(queue_workboard, dict)
        self.assertIn("mismatch_count", queue_workboard)
        self.assertIn("oldest_mismatch_age_s", queue_workboard)

    def test_default_public_base_urls_follow_ec2_runtime(self) -> None:
        with patch.dict(fc_doctor.os.environ, {}, clear=True):
            self.assertEqual(fc_doctor._default_api_base_url(), "http://3.98.20.77")
            self.assertEqual(fc_doctor._default_monitor_base_url(), "http://3.98.20.77:8080")

        with patch.dict(
            fc_doctor.os.environ,
            {
                "FC_PUBLIC_APP_BASE_URL": "http://public-app.example",
                "FC_PUBLIC_MONITOR_BASE_URL": "http://public-monitor.example",
            },
            clear=True,
        ):
            self.assertEqual(fc_doctor._default_api_base_url(), "http://public-app.example")
            self.assertEqual(fc_doctor._default_monitor_base_url(), "http://public-monitor.example")

        with patch.dict(
            fc_doctor.os.environ,
            {
                "FC_PUBLIC_APP_BASE_URL": "http://public-app.example",
                "FC_PUBLIC_MONITOR_BASE_URL": "http://public-monitor.example",
                "FC_API_BASE_URL": "http://explicit-api.example",
                "FC_MONITOR_BASE_URL": "http://explicit-monitor.example",
            },
            clear=True,
        ):
            self.assertEqual(fc_doctor._default_api_base_url(), "http://explicit-api.example")
            self.assertEqual(fc_doctor._default_monitor_base_url(), "http://explicit-monitor.example")

    def test_remote_control_plane_checks_become_advisory_on_noncanonical_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runtime_state_dir = root / "logs-codex-runs" / "orchestrator-state"
            runtime_state_dir.mkdir(parents=True, exist_ok=True)
            (runtime_state_dir / "runtime-state.json").write_text(
                json.dumps({"lifecycle": "running", "execution_mode": "planner_experimental"}),
                encoding="utf-8",
            )
            scheduler = fc_doctor.check_scheduler_authority(root)
            sessions = fc_doctor.check_sessions(root)
            runtime_truth = fc_doctor.check_runtime_truth(root)
            openclaw = fc_doctor.check_openclaw_gateway(root)

        self.assertEqual(scheduler.status, "ok")
        self.assertEqual(scheduler.detail.get("control_plane_location"), "remote_vm")
        self.assertTrue(scheduler.detail.get("advisory_only"))
        self.assertEqual(sessions.status, "ok")
        self.assertEqual(sessions.detail.get("control_plane_location"), "remote_vm")
        self.assertTrue(sessions.detail.get("advisory_only"))
        self.assertEqual(runtime_truth.status, "ok")
        self.assertEqual(runtime_truth.detail.get("runtime_truth_source"), "remote_vm")
        self.assertEqual(runtime_truth.detail.get("control_plane_location"), "remote_vm")
        self.assertTrue(runtime_truth.detail.get("advisory_only"))
        self.assertEqual(openclaw.status, "ok")
        self.assertEqual(openclaw.detail.get("control_plane_location"), "remote_vm")
        self.assertTrue(openclaw.detail.get("advisory_only"))

    def test_build_payload_treats_planner_dispatch_as_advisory(self) -> None:
        ok = fc_doctor.CheckResult(status="ok", detail={})
        degraded = fc_doctor.CheckResult(status="ok", detail={"status": "ok", "advisory_state": "degraded"})
        with ExitStack() as stack:
            stack.enter_context(patch.object(fc_doctor, "_runtime_state_detail", return_value={"lifecycle": "running"}))
            stack.enter_context(patch.object(fc_doctor, "check_workspace_root", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_plane_planning", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_runtime_truth", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_openclaw_gateway", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_scheduler_authority", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_sessions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_locks", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_queue_workboard", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_providers", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_product_value", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_future_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_browser_proof_pipeline", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_suspicious_completions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_qa_review_pipeline", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_execution_model", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_progress_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_orphan_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_capability_stall_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_capability_result_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_planner_takeover_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_historical_delivery_debt", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_planner_dispatch", return_value=degraded))
            payload, code = fc_doctor.build_payload(
                root=ROOT,
                api_base="http://127.0.0.1:8050",
                monitor_base="http://127.0.0.1:7779",
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["checks"]["planner_dispatch"]["status"], "ok")
        self.assertEqual(payload["checks"]["planner_dispatch"]["advisory_state"], "degraded")

    def test_build_payload_treats_browser_proof_pipeline_as_advisory(self) -> None:
        ok = fc_doctor.CheckResult(status="ok", detail={})
        degraded = fc_doctor.CheckResult(status="degraded", detail={"status": "degraded", "missing_task_ids": ["BATCH-89-ADMIN-01"]})
        with ExitStack() as stack:
            stack.enter_context(patch.object(fc_doctor, "_runtime_state_detail", return_value={"lifecycle": "running"}))
            stack.enter_context(patch.object(fc_doctor, "check_workspace_root", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_plane_planning", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_runtime_truth", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_openclaw_gateway", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_scheduler_authority", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_sessions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_locks", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_queue_workboard", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_providers", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_product_value", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_future_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_browser_proof_pipeline", return_value=degraded))
            stack.enter_context(patch.object(fc_doctor, "check_suspicious_completions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_qa_review_pipeline", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_execution_model", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_progress_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_orphan_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_capability_stall_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_capability_result_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_planner_takeover_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_historical_delivery_debt", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_planner_dispatch", return_value=ok))
            payload, code = fc_doctor.build_payload(
                root=ROOT,
                api_base="http://127.0.0.1:8050",
                monitor_base="http://127.0.0.1:7779",
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["checks"]["browser_proof_pipeline"]["status"], "degraded")

    def test_delivery_control_metrics_is_computed_once_per_doctor_run(self) -> None:
        calls = {"count": 0}

        class FakeGuard:
            @staticmethod
            def build_delivery_control_metrics(root: Path, window_hours: int = 24) -> dict:
                calls["count"] += 1
                return {
                    "future_status": "ok",
                    "future_delivery_integrity": {"status": "ok"},
                    "browser_proof_pipeline": {"status": "ok"},
                    "suspicious_completions": {"count": 0},
                    "qa_review_pipeline": {"status": "ok"},
                    "capability_stall_summary": {"count": 0, "items": []},
                    "historical_debt": {"count": 0},
                }

        ok = fc_doctor.CheckResult(status="ok", detail={})
        runtime_truth_ok = fc_doctor.CheckResult(
            status="ok",
            detail={"event_store_primary": True, "runtime_truth_source": "sqlite", "agentic_runtime": {"status": "ok"}},
        )
        planner_ok = fc_doctor.CheckResult(status="ok", detail={"status": "ok", "event_store_primary": True})
        with ExitStack() as stack:
            stack.enter_context(patch.object(fc_doctor, "_runtime_state_detail", return_value={"lifecycle": "running"}))
            stack.enter_context(patch.object(fc_doctor, "_worker_runtime_snapshot", return_value={}))
            stack.enter_context(patch.object(fc_doctor, "_load_product_priority_guard", return_value=FakeGuard))
            stack.enter_context(patch.object(fc_doctor, "check_workspace_root", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_plane_planning", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_runtime_truth", return_value=runtime_truth_ok))
            stack.enter_context(patch.object(fc_doctor, "check_openclaw_gateway", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_scheduler_authority", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_sessions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_locks", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_queue_workboard", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_providers", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_product_value", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_execution_model", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_progress_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_dev_orphan_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_capability_result_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_planner_dispatch", return_value=planner_ok))
            payload, code = fc_doctor.build_payload(
                root=ROOT,
                api_base="http://127.0.0.1:8050",
                monitor_base="http://127.0.0.1:7779",
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(calls["count"], 1)

    def test_planner_dispatch_metrics_is_computed_once_per_doctor_run(self) -> None:
        calls = {"count": 0}

        class FakeDispatch:
            @staticmethod
            def build_planner_dispatch_metrics(root: Path, recent_limit: int = 12) -> dict:
                calls["count"] += 1
                return {
                    "status": "ok",
                    "event_store_primary": True,
                    "runtime_truth_source": "sqlite",
                    "recent_invalid_result_count": 0,
                    "recent_timeout_like_count": 0,
                    "dev_no_progress_count": 0,
                    "dev_orphaned_count": 0,
                    "recovering": False,
                    "latest_failure_mode": "none",
                    "long_running_dev_count": 0,
                    "dev_invalid_result_count": 0,
                    "dev_timeout_like_count": 0,
                    "dev_tasks_needing_recovery": [],
                    "recovery_mode": "none",
                }

        ok = fc_doctor.CheckResult(status="ok", detail={})
        runtime_truth_ok = fc_doctor.CheckResult(
            status="ok",
            detail={"event_store_primary": True, "runtime_truth_source": "sqlite", "agentic_runtime": {"status": "ok"}},
        )
        with ExitStack() as stack:
            stack.enter_context(patch.object(fc_doctor, "_runtime_state_detail", return_value={"lifecycle": "running"}))
            stack.enter_context(patch.object(fc_doctor, "_worker_runtime_snapshot", return_value={}))
            stack.enter_context(patch.object(fc_doctor, "_load_planner_dispatch_metrics", return_value=FakeDispatch))
            stack.enter_context(patch.object(fc_doctor, "check_workspace_root", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_plane_planning", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_runtime_truth", return_value=runtime_truth_ok))
            stack.enter_context(patch.object(fc_doctor, "check_openclaw_gateway", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_scheduler_authority", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_sessions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_locks", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_queue_workboard", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_providers", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_product_value", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_future_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_browser_proof_pipeline", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_suspicious_completions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_qa_review_pipeline", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_capability_stall_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_planner_takeover_recovery", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_historical_delivery_debt", return_value=ok))
            payload, code = fc_doctor.build_payload(
                root=ROOT,
                api_base="http://127.0.0.1:8050",
                monitor_base="http://127.0.0.1:7779",
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(calls["count"], 1)

    def test_build_payload_skips_heavy_delivery_checks_when_runtime_is_idle(self) -> None:
        ok = fc_doctor.CheckResult(status="ok", detail={})
        runtime_truth_idle = fc_doctor.CheckResult(
            status="ok",
            detail={
                "event_store_primary": True,
                "runtime_truth_source": "sqlite",
                "graph_state_count": 0,
                "recent_event_count": 0,
                "agentic_runtime": {"status": "ok"},
            },
        )
        with ExitStack() as stack:
            stack.enter_context(patch.object(fc_doctor, "_runtime_state_detail", return_value={"lifecycle": "running"}))
            stack.enter_context(patch.object(fc_doctor, "_worker_runtime_snapshot", return_value={}))
            stack.enter_context(patch.object(fc_doctor, "check_workspace_root", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_plane_planning", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_runtime_truth", return_value=runtime_truth_idle))
            stack.enter_context(patch.object(fc_doctor, "check_openclaw_gateway", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_scheduler_authority", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_sessions", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_locks", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_queue_workboard", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_providers", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_product_value", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_integrity", return_value=ok))
            stack.enter_context(patch.object(fc_doctor, "check_delivery_future_integrity", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_browser_proof_pipeline", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_suspicious_completions", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_qa_review_pipeline", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_dev_execution_model", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_dev_progress_integrity", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_dev_orphan_recovery", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_capability_stall_recovery", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_capability_result_integrity", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_planner_takeover_recovery", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_historical_delivery_debt", side_effect=AssertionError("should not run")))
            stack.enter_context(patch.object(fc_doctor, "check_planner_dispatch", side_effect=AssertionError("should not run")))
            payload, code = fc_doctor.build_payload(
                root=ROOT,
                api_base="http://127.0.0.1:8050",
                monitor_base="http://127.0.0.1:7779",
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["checks"]["queue_workboard"]["idle_runtime_fast_path"])
        self.assertTrue(payload["checks"]["product_value"]["idle_runtime_fast_path"])
        self.assertTrue(payload["checks"]["delivery_future_integrity"]["idle_runtime_fast_path"])
        self.assertTrue(payload["checks"]["planner_dispatch"]["idle_runtime_fast_path"])

    def test_check_plane_planning_requires_active_sync_signal(self) -> None:
        with patch.object(
            fc_doctor,
            "build_plane_planning_snapshot",
            return_value={
                "status": "ok",
                "sync": {
                    "adapter_enabled": True,
                    "cache": {
                        "exists": False,
                    },
                },
            },
        ):
            result = fc_doctor.check_plane_planning(ROOT)
        self.assertEqual(result.status, "ok")

        with patch.object(
            fc_doctor,
            "build_plane_planning_snapshot",
            return_value={
                "status": "ok",
                "sync": {
                    "adapter_enabled": False,
                    "cache": {
                        "exists": False,
                    },
                },
            },
        ):
            result = fc_doctor.check_plane_planning(ROOT)
        self.assertEqual(result.status, "degraded")

    def test_check_plane_planning_unconfigured_but_guarded_is_advisory_ok(self) -> None:
        with patch.object(
            fc_doctor,
            "build_plane_planning_snapshot",
            return_value={
                "status": "unknown",
                "sync": {
                    "adapter_enabled": False,
                    "cache": {
                        "exists": False,
                    },
                },
                "docs_mode": {
                    "repo_backlog_docs_authoritative": False,
                    "repo_backlog_docs_mode": "reference_only",
                    "new_backlog_creation_allowed_in_docs": False,
                },
                "runtime_independence": {
                    "startup_blocks_on_plane": False,
                    "degraded_when_unreachable": True,
                },
            },
        ):
            result = fc_doctor.check_plane_planning(ROOT)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("advisory_state"), "unknown")

    def test_check_openclaw_gateway_reachable_but_operator_degraded_is_advisory_ok(self) -> None:
        with patch.object(fc_doctor, "_allow_live_openclaw_checks", return_value=True), \
             patch.object(fc_doctor.subprocess, "run") as mock_run, \
             patch.object(fc_doctor, "_systemd_unit_probe", side_effect=[
                {"ok": False, "output": "inactive"},
                 {"ok": False, "output": "not-found"},
             ]), \
             patch.object(fc_doctor, "_openclaw_process_probe", return_value={"gateway_running": False, "cli_running": False, "doctor_running": False, "detail": {}}), \
             patch.object(fc_doctor, "_run_openclaw_probe", side_effect=[
                 {"ok": False, "cmd": ["openclaw", "doctor"]},
                 {"ok": False, "cmd": ["openclaw", "status"]},
                 {"ok": True, "cmd": ["openclaw", "health", "--json"]},
                 {"ok": False, "cmd": ["openclaw", "models", "status", "--check"]},
             ]):
            mock_run.return_value = SimpleNamespace(returncode=0, stdout="/usr/bin/openclaw\n", stderr="")
            result = fc_doctor.check_openclaw_gateway(ROOT)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("advisory_state"), "degraded")
        self.assertEqual(result.detail.get("service_unit"), "openclaw-gateway.service")

    def test_check_openclaw_gateway_uses_process_fallback_when_cli_times_out(self) -> None:
        with patch.object(fc_doctor, "_allow_live_openclaw_checks", return_value=True), \
             patch.object(fc_doctor.subprocess, "run") as mock_run, \
             patch.object(fc_doctor, "_systemd_unit_probe", side_effect=[
                 {"ok": False, "output": "Failed to connect to bus: No medium found"},
                 {"ok": False, "output": "Failed to connect to bus: No medium found"},
             ]), \
             patch.object(
                 fc_doctor,
                 "_openclaw_process_probe",
                 return_value={
                     "gateway_running": True,
                     "cli_running": True,
                     "doctor_running": False,
                     "detail": {"gateway": {"ok": True}, "cli": {"ok": True}},
                 },
             ), \
             patch.object(fc_doctor, "_run_openclaw_probe", side_effect=[
                 {"ok": False, "cmd": ["openclaw", "doctor"], "stderr": "Command timed out after 0.5 seconds"},
                 {"ok": False, "cmd": ["openclaw", "status"], "stderr": "Command timed out after 0.5 seconds"},
                 {"ok": False, "cmd": ["openclaw", "health"], "stderr": "Command timed out after 0.5 seconds"},
                 {"ok": False, "cmd": ["openclaw", "models", "status", "--check"], "stderr": "Command timed out after 0.5 seconds"},
             ]):
            mock_run.return_value = SimpleNamespace(returncode=0, stdout="/usr/bin/openclaw\n", stderr="")
            result = fc_doctor.check_openclaw_gateway(ROOT)
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.detail.get("process_fallback_used"))
        self.assertEqual(result.detail.get("advisory_state"), "degraded")

    def test_scheduler_authority_dual_detected(self) -> None:
        def _fake_run(cmd, **kwargs):
            if cmd[:2] == ["crontab", "-l"]:
                return SimpleNamespace(returncode=0, stdout="*/2 * * * * bash scripts/vm_resume_guard.sh\n", stderr="")
            if cmd == ["which", "systemctl"]:
                return SimpleNamespace(returncode=0, stdout="/usr/bin/systemctl\n", stderr="")
            if cmd[:3] == ["systemctl", "--user", "show-environment"]:
                return SimpleNamespace(returncode=0, stdout="PATH=/usr/bin\n", stderr="")
            if cmd[:4] == ["systemctl", "--user", "is-enabled", "vm-resume-guard.timer"]:
                return SimpleNamespace(returncode=0, stdout="enabled\n", stderr="")
            if cmd[:4] == ["systemctl", "--user", "is-active", "vm-resume-guard.timer"]:
                return SimpleNamespace(returncode=0, stdout="active\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="")

        with patch.object(fc_doctor.subprocess, "run", side_effect=_fake_run):
            result = fc_doctor.check_scheduler_authority(Path("."))
        self.assertEqual(result.status, "degraded")
        self.assertEqual(result.detail.get("scheduler_policy"), "dual_authority_detected")

    def test_scheduler_authority_cron_only_ok(self) -> None:
        def _fake_run(cmd, **kwargs):
            if cmd[:2] == ["crontab", "-l"]:
                return SimpleNamespace(returncode=0, stdout="*/2 * * * * bash scripts/vm_resume_guard.sh\n", stderr="")
            if cmd == ["which", "systemctl"]:
                return SimpleNamespace(returncode=0, stdout="/usr/bin/systemctl\n", stderr="")
            if cmd[:3] == ["systemctl", "--user", "show-environment"]:
                return SimpleNamespace(returncode=0, stdout="PATH=/usr/bin\n", stderr="")
            if cmd[:4] == ["systemctl", "--user", "is-enabled", "vm-resume-guard.timer"]:
                return SimpleNamespace(returncode=1, stdout="disabled\n", stderr="")
            if cmd[:4] == ["systemctl", "--user", "is-active", "vm-resume-guard.timer"]:
                return SimpleNamespace(returncode=3, stdout="inactive\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="")

        with patch.object(fc_doctor.subprocess, "run", side_effect=_fake_run):
            result = fc_doctor.check_scheduler_authority(Path("."))
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("scheduler_policy"), "cron_only")

    def test_scheduler_authority_openclaw_cron_only_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            jobs_dir = home / ".openclaw" / "cron"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            (jobs_dir / "jobs.json").write_text(
                json.dumps(
                    {
                        "jobs": [
                            {"name": "planner-tmux-loop", "enabled": True},
                            {"name": "admin-agents-supervisor-15m", "enabled": True},
                            {"name": "vm-resume-guard-2m", "enabled": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def _fake_run(cmd, **kwargs):
                if cmd[:2] == ["crontab", "-l"]:
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                if cmd == ["which", "systemctl"]:
                    return SimpleNamespace(returncode=0, stdout="/usr/bin/systemctl\n", stderr="")
                if cmd[:3] == ["systemctl", "--user", "show-environment"]:
                    return SimpleNamespace(returncode=0, stdout="PATH=/usr/bin\n", stderr="")
                if cmd[:4] == ["systemctl", "--user", "is-enabled", "vm-resume-guard.timer"]:
                    return SimpleNamespace(returncode=1, stdout="disabled\n", stderr="")
                if cmd[:4] == ["systemctl", "--user", "is-active", "vm-resume-guard.timer"]:
                    return SimpleNamespace(returncode=3, stdout="inactive\n", stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            with patch.object(fc_doctor.subprocess, "run", side_effect=_fake_run):
                with patch.object(fc_doctor.Path, "home", return_value=home):
                    result = fc_doctor.check_scheduler_authority(Path("."))
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("scheduler_policy"), "openclaw_cron_only")
        self.assertEqual(result.detail.get("openclaw_cron_enabled_count"), 2)

    def test_scheduler_authority_permission_denied_uses_runtime_state_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )
            runtime_state_dir = root / "logs-codex-runs" / "orchestrator-state"
            runtime_state_dir.mkdir(parents=True, exist_ok=True)
            (runtime_state_dir / "runtime-state.json").write_text(
                json.dumps(
                    {
                        "execution_mode": "planner_experimental",
                        "updated_at": "2026-03-08T15:24:09Z",
                        "source": "fc_setup_crons",
                    }
                ),
                encoding="utf-8",
            )
            fake = SimpleNamespace(returncode=1, stdout="", stderr="crontabs/venom/: fopen: Permission denied")
            with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                with patch.object(fc_doctor, "datetime") as mock_datetime:
                    mock_datetime.now.return_value = __import__("datetime").datetime(2026, 3, 8, 15, 40, tzinfo=__import__("datetime").timezone.utc)
                    mock_datetime.fromisoformat.side_effect = __import__("datetime").datetime.fromisoformat
                    result = fc_doctor.check_scheduler_authority(root)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("scheduler_policy"), "probe_blocked_runtime_state_fallback")

    def test_check_sessions_permission_denied_uses_recent_tick_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )
            tick_dir = root / "logs-codex-runs" / "fc-ticks"
            tick_dir.mkdir(parents=True, exist_ok=True)
            (tick_dir / "planner.tick.log").write_text(
                "2026-03-08T15:20:00Z [END] rc=0\n",
                encoding="utf-8",
            )
            fake = SimpleNamespace(returncode=1, stdout="", stderr="error connecting to /tmp/tmux-1000/default (Operation not permitted)")
            with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                with patch.object(fc_doctor, "datetime") as mock_datetime:
                    mock_datetime.now.return_value = __import__("datetime").datetime(2026, 3, 8, 15, 40, tzinfo=__import__("datetime").timezone.utc)
                    mock_datetime.fromisoformat.side_effect = __import__("datetime").datetime.fromisoformat
                    result = fc_doctor.check_sessions(root)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("fallback_source"), "fc_ticks")
        self.assertEqual(result.detail.get("missing_core"), [])

    def test_check_providers_permission_denied_uses_listener_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            def _fake_probe(url: str, timeout_s: float):
                return (False, 0, "<urlopen error [Errno 1] Operation not permitted>")

            def _fake_run(cmd, **kwargs):
                if cmd[:2] == ["ss", "-ltn"]:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=(
                            "State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
                            "LISTEN 0 0 127.0.0.1:8050 0.0.0.0:*\n"
                            "LISTEN 0 0 0.0.0.0:7779 0.0.0.0:*\n"
                        ),
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            with patch.object(fc_doctor, "_probe_json", side_effect=_fake_probe):
                with patch.object(fc_doctor.subprocess, "run", side_effect=_fake_run):
                    result = fc_doctor.check_providers(
                        root=Path("."),
                        api_base="http://127.0.0.1:8050",
                        monitor_base="http://127.0.0.1:7779",
                        state_dir=state_dir,
                    )
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.detail.get("api_listener_ok"))
        self.assertTrue(result.detail.get("monitor_listener_ok"))

    def test_check_sessions_permission_denied_uses_planner_dispatch_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_dir = root / "platform" / "config" / "runner"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "runner.v1.yaml").write_text(
                json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
                encoding="utf-8",
            )
            tick_dir = root / "logs-codex-runs" / "fc-ticks"
            tick_dir.mkdir(parents=True, exist_ok=True)
            (tick_dir / "planner.tick.log").write_text(
                "2026-03-08T11:31:38Z [END] rc=0\n",
                encoding="utf-8",
            )
            orch_dir = root / "docs" / "operations" / "orchestrator"
            orch_dir.mkdir(parents=True, exist_ok=True)
            (orch_dir / "planner-subagents-registry.json").write_text(
                json.dumps(
                    {
                        "updated_at": "2026-03-08T15:31:44Z",
                        "subagents": [
                            {
                                "status": "running",
                                "last_update_at": "2026-03-08T15:31:44Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fake = SimpleNamespace(returncode=1, stdout="", stderr="error connecting to /tmp/tmux-1000/default (Operation not permitted)")
            with patch.object(fc_doctor.subprocess, "run", return_value=fake):
                with patch.object(fc_doctor, "datetime") as mock_datetime:
                    mock_datetime.now.return_value = __import__("datetime").datetime(2026, 3, 8, 15, 40, tzinfo=__import__("datetime").timezone.utc)
                    mock_datetime.fromisoformat.side_effect = __import__("datetime").datetime.fromisoformat
                    result = fc_doctor.check_sessions(root)
        self.assertEqual(result.status, "degraded")
        self.assertEqual(result.detail.get("missing_core"), ["planner"])
        self.assertEqual(result.detail.get("found_core", {}), {})


if __name__ == "__main__":
    unittest.main()
