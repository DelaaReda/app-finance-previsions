#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSTREAM = ROOT / "scripts" / "parallel_workstream.py"


class ParallelWorkstreamChannelsTests(unittest.TestCase):
    def test_channels_context_is_available_for_all_roles(self) -> None:
        roles = [
            "planner",
            "analyst",
            "architect",
            "po",
            "scrum_master",
            "backend_engineer",
            "frontend_engineer",
            "data_analyst",
            "infra_engineer",
            "integrator",
            "dev",
            "tester",
            "qa",
            "clawsentinel",
        ]
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            init = subprocess.run(
                [sys.executable, str(WORKSTREAM), "--board", str(board_path), "init", "--force"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, msg=init.stderr)
            for role in roles:
                cp = subprocess.run(
                    [sys.executable, str(WORKSTREAM), "--board", str(board_path), "channels", "--role", role, "--limit", "2"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(cp.returncode, 0, msg=f"role={role} stderr={cp.stderr}")
                self.assertIn(f"CHANNELS_CONTEXT role={role}", cp.stdout)
                self.assertIn("impact_level=", cp.stdout)
                self.assertIn("impact_action=", cp.stdout)
                self.assertIn("status_ready=", cp.stdout)
                self.assertIn("status_in_progress=", cp.stdout)
                self.assertIn("status_done=", cp.stdout)


if __name__ == "__main__":
    unittest.main()
