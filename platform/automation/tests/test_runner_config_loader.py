from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOADER = ROOT / "platform" / "automation" / "runner" / "config_loader.py"
CFG = ROOT / "platform" / "config" / "runner" / "runner.v1.yaml"
SCHEMA = ROOT / "platform" / "config" / "schema" / "runner.v1.schema.json"


class RunnerConfigLoaderTests(unittest.TestCase):
    def test_validate_ok(self) -> None:
        cp = subprocess.run(
            ["python3", str(LOADER), "--config", str(CFG), "--schema", str(SCHEMA), "validate"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        payload = json.loads(cp.stdout.strip() or "{}")
        self.assertTrue(payload.get("ok"), msg=payload)

    def test_emit_env_for_dev(self) -> None:
        cp = subprocess.run(
            ["python3", str(LOADER), "--config", str(CFG), "--schema", str(SCHEMA), "emit-env", "--role", "dev"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        lines = [line for line in cp.stdout.splitlines() if line and not line.startswith("#")]
        self.assertTrue(any(line.startswith("FC_DEV_PROMPT_TIMEOUT_SECONDS=") for line in lines))
        self.assertTrue(any(line.startswith("TMUX_ROLE_CODEX_EXEC_RESUME=") for line in lines))
        self.assertTrue(any(line.startswith("RUNNER_CONFIG_SOURCE=") for line in lines))
        self.assertTrue(any(line.startswith("RUNNER_CONFIG_HASH=") for line in lines))
        self.assertTrue(any(line.startswith("FC_API_AUTONOMY_MODE=") for line in lines))
        self.assertTrue(any(line.startswith("FC_API_WAVE_MANIFEST_PATH=") for line in lines))
        self.assertTrue(any(line.startswith("FC_API_WAVE_BATCH_ID=") for line in lines))

    def test_cli_set_precedence(self) -> None:
        cp = subprocess.run(
            [
                "python3",
                str(LOADER),
                "--config",
                str(CFG),
                "--schema",
                str(SCHEMA),
                "--set",
                "roles.dev.prompt_timeout_seconds=444",
                "emit-env",
                "--role",
                "dev",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("FC_DEV_PROMPT_TIMEOUT_SECONDS='444'", cp.stdout)

    def test_invalid_config_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad_cfg = Path(td) / "bad.json"
            bad_cfg.write_text("{}", encoding="utf-8")
            cp = subprocess.run(
                ["python3", str(LOADER), "--config", str(bad_cfg), "--schema", str(SCHEMA), "validate"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(cp.returncode, 0)
            payload = json.loads(cp.stdout.strip() or "{}")
            self.assertFalse(payload.get("ok", True))

    def test_env_whitelist_override(self) -> None:
        env = os.environ.copy()
        env["FC_DEV_PROMPT_TIMEOUT_SECONDS"] = "333"
        cp = subprocess.run(
            ["python3", str(LOADER), "--config", str(CFG), "--schema", str(SCHEMA), "emit-env", "--role", "dev"],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("FC_DEV_PROMPT_TIMEOUT_SECONDS='333'", cp.stdout)


if __name__ == "__main__":
    unittest.main()
