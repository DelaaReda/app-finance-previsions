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
        for key in ("workspace_root", "scheduler_authority", "sessions", "locks", "queue_workboard", "providers", "product_value", "delivery_integrity"):
            self.assertIn(key, payload["checks"])
        queue_workboard = payload["checks"].get("queue_workboard", {})
        self.assertIsInstance(queue_workboard, dict)
        self.assertIn("mismatch_count", queue_workboard)
        self.assertIn("oldest_mismatch_age_s", queue_workboard)

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


if __name__ == "__main__":
    unittest.main()
