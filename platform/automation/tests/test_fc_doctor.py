#!/usr/bin/env python3
from __future__ import annotations

import unittest
import importlib.util
import sys
import json
import tempfile
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

    def test_build_payload_treats_planner_dispatch_as_advisory(self) -> None:
        ok = fc_doctor.CheckResult(status="ok", detail={})
        degraded = fc_doctor.CheckResult(status="degraded", detail={"status": "degraded"})
        with patch.object(fc_doctor, "_runtime_state_detail", return_value={"lifecycle": "running"}):
            with patch.object(fc_doctor, "check_workspace_root", return_value=ok):
                with patch.object(fc_doctor, "check_scheduler_authority", return_value=ok):
                    with patch.object(fc_doctor, "check_sessions", return_value=ok):
                        with patch.object(fc_doctor, "check_locks", return_value=ok):
                            with patch.object(fc_doctor, "check_queue_workboard", return_value=ok):
                                with patch.object(fc_doctor, "check_providers", return_value=ok):
                                    with patch.object(fc_doctor, "check_product_value", return_value=ok):
                                        with patch.object(fc_doctor, "check_delivery_integrity", return_value=ok):
                                            with patch.object(fc_doctor, "check_delivery_future_integrity", return_value=ok):
                                                with patch.object(fc_doctor, "check_browser_proof_pipeline", return_value=ok):
                                                    with patch.object(fc_doctor, "check_suspicious_completions", return_value=ok):
                                                        with patch.object(fc_doctor, "check_qa_review_pipeline", return_value=ok):
                                                            with patch.object(fc_doctor, "check_dev_execution_model", return_value=ok):
                                                                with patch.object(fc_doctor, "check_dev_progress_integrity", return_value=ok):
                                                                    with patch.object(fc_doctor, "check_dev_orphan_recovery", return_value=ok):
                                                                        with patch.object(fc_doctor, "check_capability_result_integrity", return_value=ok):
                                                                            with patch.object(fc_doctor, "check_planner_takeover_recovery", return_value=ok):
                                                                                with patch.object(fc_doctor, "check_planner_dispatch", return_value=degraded):
                                                                                    payload, code = fc_doctor.build_payload(
                                                                                        root=ROOT,
                                                                                        api_base="http://127.0.0.1:8050",
                                                                                        monitor_base="http://127.0.0.1:7779",
                                                                                    )
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["checks"]["planner_dispatch"]["status"], "degraded")

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
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("missing_core"), [])
        self.assertIn("planner", result.detail.get("found_core", {}))


if __name__ == "__main__":
    unittest.main()
