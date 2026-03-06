#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation" / "role_runtime_context.py"
RUNNER = ROOT / "automation" / "cron_tmux_role_runner.sh"


def _run_context(workboard_role_has_work: str, workboard_role_has_ready: str, workboard_role_has_in_progress: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        (workspace / "docs/orchestrator-ops").mkdir(parents=True, exist_ok=True)
        (workspace / "docs/planning").mkdir(parents=True, exist_ok=True)
        (workspace / "state").mkdir(parents=True, exist_ok=True)
        (workspace / "memory/agents").mkdir(parents=True, exist_ok=True)
        (workspace / "docs/ops").mkdir(parents=True, exist_ok=True)
        (workspace / "logs").mkdir(parents=True, exist_ok=True)

        (workspace / "docs/orchestrator-ops/priority-queue.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )
        (workspace / "docs/planning/WORKSTATE.md").write_text("none\n", encoding="utf-8")
        (workspace / "state/dev.last_contract").write_text(
            "STATUS: IN_PROGRESS\nDELTA: DEV_TICK\nNEXT_ACTION_UNIQUE: DEV_ACTION\n",
            encoding="utf-8",
        )
        (workspace / "memory/agents/dev.md").write_text("# dev\n", encoding="utf-8")
        (workspace / "docs/ops/ADMIN_TEAM_CHAT.md").write_text("chat\n", encoding="utf-8")
        (workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md").write_text("iter\n", encoding="utf-8")
        (workspace / "docs/ops/DIRECTIVE_BUS.jsonl").write_text("", encoding="utf-8")
        (workspace / "docs/ops/AGENT_MESSAGE_BUS.jsonl").write_text("", encoding="utf-8")
        (workspace / "logs/dev.live.log").write_text("trace\n", encoding="utf-8")

        cp = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "dev",
                str(workspace),
                str(workspace / "state"),
                str(workspace / "memory/agents"),
                str(workspace / "docs/ops/ADMIN_TEAM_CHAT.md"),
                str(workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md"),
                str(workspace / "docs/ops/DIRECTIVE_BUS.jsonl"),
                str(workspace / "logs/dev.live.log"),
                str(workspace / "state/dev.last_contract"),
                "queue_v_test",
                "workboard_v_test",
                workboard_role_has_work,
                workboard_role_has_ready,
                workboard_role_has_in_progress,
                str(workspace / "docs/ops/AGENT_MESSAGE_BUS.jsonl"),
                "3",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if cp.returncode != 0:
            raise AssertionError(cp.stderr)
        return cp.stdout.strip()


class DevWaitReadyTaskOnlyTests(unittest.TestCase):
    def test_dev_wait_allowed_only_when_no_ready_and_no_in_progress(self) -> None:
        out = _run_context("0", "0", "0")
        self.assertIn("dev_has_ready_task=0", out)
        self.assertIn("dev_wait_allowed=1", out)

        out = _run_context("1", "1", "0")
        self.assertIn("dev_has_ready_task=1", out)
        self.assertIn("dev_wait_allowed=0", out)

        out = _run_context("1", "0", "1")
        self.assertIn("dev_has_ready_task=0", out)
        self.assertIn("dev_wait_allowed=0", out)

    def test_runner_contains_dev_wait_policy_enforcement(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('TMUX_ROLE_DEV_WAIT_READY_TASK_ONLY="${TMUX_ROLE_DEV_WAIT_READY_TASK_ONLY:-1}"', text)
        self.assertIn('values["NEXT"] = "owner=dev; action=claim_or_progress_now"', text)
        self.assertIn('values["DELTA"] = "DEV_WAIT_NO_READY_TASK"', text)


if __name__ == "__main__":
    unittest.main()
