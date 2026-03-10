#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SET_MODE_PATH = ROOT / "platform" / "automation" / "set_orchestration_mode.sh"
FC_AGENT_TICK_PATH = ROOT / "scripts" / "fc_agent_tick.sh"
FC_DOCTOR_PATH = ROOT / "platform" / "automation" / "fc_doctor.py"
DOCTOR_PATH = ROOT / "platform" / "automation" / "doctor.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fc_doctor = _load_module("fc_doctor_runtime_control_tests", FC_DOCTOR_PATH)
doctor = _load_module("doctor_runtime_control_tests", DOCTOR_PATH)


class RuntimeControlPlaneTests(unittest.TestCase):
    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _make_workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tempdir = tempfile.TemporaryDirectory()
        root = Path(tempdir.name)
        (root / "docs" / "orchestrator-ops").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "operations" / "orchestrator").mkdir(parents=True, exist_ok=True)
        (root / "logs-codex-runs" / "orchestrator-state").mkdir(parents=True, exist_ok=True)
        (root / "platform" / "config" / "runner").mkdir(parents=True, exist_ok=True)
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        return tempdir, root

    def _write_runtime_state(
        self,
        root: Path,
        *,
        lifecycle: str = "running",
        reason: str = "test",
        execution_mode: str = "planner_experimental",
        operator_mode: str = "planner-only",
    ) -> None:
        self._write_json(
            root / "logs-codex-runs" / "orchestrator-state" / "runtime-state.json",
            {
                "lifecycle": lifecycle,
                "reason": reason,
                "execution_mode": execution_mode,
                "operator_mode": operator_mode,
                "source": "tests",
            },
        )

    def _write_runner_config(self, root: Path, *, planner_only: bool = True) -> None:
        self._write_json(
            root / "platform" / "config" / "runner" / "runner.v1.yaml",
            {
                "features": {
                    "planner_orchestrator": {
                        "enabled": 1 if planner_only else 0,
                        "cron_planner_only": 1 if planner_only else 0,
                    }
                }
            },
        )

    def _write_role_map(self, root: Path) -> None:
        self._write_json(
            root / "docs" / "orchestrator-ops" / "parallel-role-cron-map.json",
            {
                "roles": [
                    {"role": "planner", "id": "job-planner", "name": "planner-tmux-loop", "session_name": "codex_planner_cron"},
                    {"role": "dev", "id": "job-dev", "name": "dev-tmux-loop", "session_name": "codex_dev_cron"},
                    {"role": "admin", "id": "job-admin", "name": "admin-tmux-loop", "session_name": "codex_admin_cron"},
                    {"role": "scrum_master", "id": "job-scrum", "name": "scrum-master-tmux-loop", "session_name": "codex_scrum_master_cron"},
                ]
            },
        )

    def _write_openclaw_stub(self, root: Path, jobs: list[dict[str, object]]) -> None:
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        state_file = root / "openclaw-state.json"
        self._write_json(state_file, {"jobs": jobs})
        (bin_dir / "openclaw").write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                from pathlib import Path

                state_path = Path(os.environ["OPENCLAW_STATE_FILE"])
                payload = json.loads(state_path.read_text(encoding="utf-8"))
                jobs = payload.get("jobs", [])
                args = sys.argv[1:]

                if args[:3] == ["cron", "list", "--all"] and "--json" in args:
                    print(json.dumps(payload))
                    raise SystemExit(0)
                if args[:2] == ["cron", "list"] and "--json" in args:
                    print(json.dumps(payload))
                    raise SystemExit(0)
                if args[:2] == ["cron", "list"]:
                    for job in jobs:
                        print(f"{job.get('id','')}\\t{job.get('name','')}\\tenabled={job.get('enabled', False)}")
                    raise SystemExit(0)
                if args[:2] in (["cron", "enable"], ["cron", "disable"]):
                    target = args[2]
                    enabled = args[1] == "enable"
                    for job in jobs:
                        if str(job.get("id")) == target:
                            job["enabled"] = enabled
                    state_path.write_text(json.dumps(payload), encoding="utf-8")
                    raise SystemExit(0)
                raise SystemExit(0)
                """
            ),
            encoding="utf-8",
        )
        (bin_dir / "openclaw").chmod(0o755)
        (bin_dir / "tmux").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (bin_dir / "tmux").chmod(0o755)

    def _base_env(self, root: Path) -> dict[str, str]:
        env = dict(os.environ)
        env["FC_WORKSPACE_ROOT"] = str(root)
        env["OPENCLAW_STATE_FILE"] = str(root / "openclaw-state.json")
        env["PATH"] = f"{root / 'bin'}:{env.get('PATH', '')}"
        env["FC_STATE_RECONCILER"] = "0"
        return env

    def _write_queue_and_workboard(self, root: Path, *, queue_state: str, workboard_state: str) -> None:
        self._write_json(
            root / "logs-codex-runs" / "orchestrator-state" / "priority-queue.json",
            {"items": [{"id": "BATCH-15", "state": queue_state, "updated_at": "2026-03-09T20:00:00Z"}]},
        )
        self._write_json(
            root / "logs-codex-runs" / "orchestrator-state" / "parallel-workstreams.json",
            {
                "tasks": [
                    {
                        "id": "BATCH-15-ARCH",
                        "stream_id": "BATCH-15",
                        "state": workboard_state,
                        "updated_at": "2026-03-09T20:00:00Z",
                    }
                ]
            },
        )

    def test_set_orchestration_mode_parallel_resolves_to_planner_only(self) -> None:
        tempdir, root = self._make_workspace()
        self.addCleanup(tempdir.cleanup)
        self._write_runtime_state(root, lifecycle="running", reason="cron_profile_full")
        self._write_role_map(root)
        self._write_openclaw_stub(
            root,
            jobs=[
                {"id": "job-planner", "name": "planner-tmux-loop", "enabled": False},
                {"id": "job-dev", "name": "dev-tmux-loop", "enabled": False},
                {"id": "job-admin", "name": "admin-tmux-loop", "enabled": False},
                {"id": "job-scrum", "name": "scrum-master-tmux-loop", "enabled": False},
                {"id": "job-gov", "name": "admin-agents-supervisor-15m", "enabled": False},
                {"id": "job-advisory", "name": "po-scrum-master-advisory-5m", "enabled": False},
            ],
        )

        res = subprocess.run(
            ["bash", str(SET_MODE_PATH), "--mode", "parallel"],
            cwd=root,
            env=self._base_env(root),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("effective_mode=planner-only", res.stdout + res.stderr)
        state = json.loads((root / "openclaw-state.json").read_text(encoding="utf-8"))
        self.assertTrue(all(job.get("enabled") is False for job in state.get("jobs", [])))
        runtime_state = json.loads(
            (root / "logs-codex-runs" / "orchestrator-state" / "runtime-state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(runtime_state.get("operator_mode"), "planner-only")
        self.assertEqual(runtime_state.get("execution_mode"), "planner_experimental")
        self.assertEqual(runtime_state.get("lifecycle"), "running")

    def test_set_orchestration_mode_paused_makes_tick_inert(self) -> None:
        tempdir, root = self._make_workspace()
        self.addCleanup(tempdir.cleanup)
        self._write_runtime_state(root, lifecycle="running", reason="cron_profile_full")
        self._write_role_map(root)
        self._write_openclaw_stub(root, jobs=[{"id": "job-planner", "name": "planner-tmux-loop", "enabled": False}])
        runner_stub = root / "scripts" / "cron_tmux_role_runner.sh"
        runner_stub.write_text(
            "#!/usr/bin/env bash\nprintf 'runner-called\\n' >> \"$PWD/runner.called\"\n",
            encoding="utf-8",
        )
        runner_stub.chmod(0o755)

        pause_res = subprocess.run(
            ["bash", str(SET_MODE_PATH), "--mode", "paused"],
            cwd=root,
            env=self._base_env(root),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(pause_res.returncode, 0, msg=pause_res.stderr)
        runtime_state = json.loads(
            (root / "logs-codex-runs" / "orchestrator-state" / "runtime-state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(runtime_state.get("lifecycle"), "paused")

        tick_res = subprocess.run(
            ["bash", str(FC_AGENT_TICK_PATH), "planner"],
            cwd=root,
            env=self._base_env(root),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tick_res.returncode, 0, msg=tick_res.stderr)
        self.assertIn("RUNTIME_INERT", tick_res.stderr)
        self.assertFalse((root / "runner.called").exists())

    def test_doctor_json_normalizes_terminal_state_and_reports_orphans(self) -> None:
        tempdir, root = self._make_workspace()
        self.addCleanup(tempdir.cleanup)
        self._write_runner_config(root, planner_only=True)
        self._write_runtime_state(root, lifecycle="running", reason="cron_profile_full")
        self._write_queue_and_workboard(root, queue_state="CLOSED", workboard_state="DONE")

        with patch.object(doctor, "_tmux_sessions", return_value=["codex_planner_cron", "codex_scrum_master_cron"]):
            with patch.object(doctor, "_quarantined_jobs", return_value=["dev-tmux-loop", "admin-agents-supervisor-15m"]):
                payload = doctor.build_payload(root, root / ".state")

        self.assertEqual(payload["sessions"]["expected"], ["codex_planner_cron"])
        self.assertIn("codex_scrum_master_cron", payload["sessions"]["orphans"])
        self.assertIn("dev-tmux-loop", payload["sessions"]["quarantined_jobs"])
        self.assertNotIn("queue_workboard_mismatch", payload["warnings"])

    def test_doctor_json_keeps_warning_for_real_mismatch(self) -> None:
        tempdir, root = self._make_workspace()
        self.addCleanup(tempdir.cleanup)
        self._write_runner_config(root, planner_only=True)
        self._write_runtime_state(root, lifecycle="running", reason="cron_profile_full")
        self._write_queue_and_workboard(root, queue_state="READY_DEV", workboard_state="WAITING_DEP")

        with patch.object(doctor, "_tmux_sessions", return_value=["codex_planner_cron"]):
            with patch.object(doctor, "_quarantined_jobs", return_value=[]):
                payload = doctor.build_payload(root, root / ".state")

        self.assertIn("queue_workboard_mismatch", payload["warnings"])
        self.assertTrue(payload["orchestrator"]["consistency_flags"]["queue_workboard_mismatch"])

    def test_fc_doctor_planner_only_keeps_planner_as_only_expected_core(self) -> None:
        tempdir, root = self._make_workspace()
        self.addCleanup(tempdir.cleanup)
        self._write_runner_config(root, planner_only=True)
        self._write_runtime_state(root, lifecycle="running", reason="cron_profile_full")
        fake = type("FakeCompleted", (), {"returncode": 0, "stdout": "codex_planner_cron\n", "stderr": ""})()

        with patch.object(fc_doctor.subprocess, "run", return_value=fake):
            with patch.object(fc_doctor, "_quarantined_jobs", return_value=["dev-tmux-loop"]):
                result = fc_doctor.check_sessions(root)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail.get("expected_core"), ["planner"])
        self.assertEqual(result.detail.get("expected"), ["codex_planner_cron"])
        self.assertEqual(result.detail.get("missing_core"), [])
        self.assertEqual(result.detail.get("execution_mode"), "planner_experimental")


if __name__ == "__main__":
    unittest.main()
