#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "platform" / "automation" / "runner_config.py"
DEFAULT_CONFIG = ROOT / "platform" / "config" / "runner" / "runner.v1.yaml"


def run_cfg(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


class RunnerConfigTests(unittest.TestCase):
    def test_validate_default_config(self) -> None:
        cp = run_cfg("--config", str(DEFAULT_CONFIG), "validate")
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        payload = json.loads(cp.stdout)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("version"), "v1")

    def test_emit_env_includes_backend_by_role_mapping(self) -> None:
        cp = run_cfg("--config", str(DEFAULT_CONFIG), "emit-env", "--role", "planner", "--fallback-env", "0")
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("FC_PLANNER_ORCHESTRATOR_BACKEND='auto'", cp.stdout)
        self.assertIn("FC_PLANNER_ORCHESTRATOR_BACKEND_BY_ROLE='", cp.stdout)
        self.assertIn("admin=codex_exec", cp.stdout)
        self.assertIn("dev=openclaw", cp.stdout)
        self.assertIn("TMUX_ROLE_RATE_LIMIT_PRECHECK='1'", cp.stdout)
        self.assertIn("TMUX_ROLE_RATE_LIMIT_QWEN_FALLBACK='1'", cp.stdout)

    def test_validate_rejects_missing_top_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "runner.v1.yaml"
            cfg.write_text(json.dumps({"version": "v1"}), encoding="utf-8")
            cp = run_cfg("--config", str(cfg), "validate")
            self.assertNotEqual(cp.returncode, 0)
            payload = json.loads(cp.stdout)
            self.assertFalse(payload.get("ok"))
            self.assertIn("missing_top_key:defaults", payload.get("errors", []))

    def test_emit_env_strict_fails_when_required_keys_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "runner.v1.yaml"
            cfg.write_text(
                json.dumps(
                    {
                        "version": "v1",
                        "defaults": {},
                        "features": {},
                        "paths": {},
                        "timeouts": {},
                        "retries": {},
                        "telemetry": {},
                        "roles": {
                            "planner": {},
                            "dev": {},
                            "admin": {},
                            "scrum_master": {},
                        },
                    }
                ),
                encoding="utf-8",
            )
            cp = run_cfg(
                "--config",
                str(cfg),
                "emit-env",
                "--role",
                "planner",
                "--fallback-env",
                "0",
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("missing_config_keys", cp.stderr)

    def test_emit_env_fallback_warns_and_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "runner.v1.yaml"
            cfg.write_text(
                json.dumps(
                    {
                        "version": "v1",
                        "defaults": {},
                        "features": {},
                        "paths": {},
                        "timeouts": {},
                        "retries": {},
                        "telemetry": {},
                        "roles": {
                            "planner": {},
                            "dev": {},
                            "admin": {},
                            "scrum_master": {},
                        },
                    }
                ),
                encoding="utf-8",
            )
            cp = run_cfg(
                "--config",
                str(cfg),
                "emit-env",
                "--role",
                "admin",
                "--fallback-env",
                "1",
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("config_fallback_env_used", cp.stderr)
            self.assertIn("RUNNER_CONFIG_VERSION=", cp.stdout)
            self.assertIn("RUNNER_CONFIG_SOURCE=", cp.stdout)
            self.assertIn("RUNNER_CONFIG_HASH=", cp.stdout)


if __name__ == "__main__":
    unittest.main()
