#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / "scripts" / "role_execution_monitoring.py"


class RoleExecutionMonitoringTests(unittest.TestCase):
    def test_writes_latest_events_and_dedupes_tool_request_line(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DEV_BATCH02_PROGRESS",
                (
                    "EVIDENCE: exec_report=patch_applied; issues=missing_tool_x; suggestions=install_tool_x; "
                    "stream_id=BATCH-02; task_id=BATCH-02-DEV; tool_request=shellcheck; skill_request=none; "
                    "channels_read=workboard_tasks; impact_assessment=medium; impact_action=sync_cross_role"
                ),
                "RISKS: missing tool",
                "NEXT: owner=adminapp-codex; action=install_shellcheck",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_MONITOR_TEST",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload_file = root / "payload.txt"
            latest_file = root / "docs" / "executors-monitoring-latest.json"
            events_file = root / "logs" / "events.jsonl"
            tool_md_file = root / "docs" / "AGENT_TOOL_REQUESTS.md"
            tool_events_file = root / "docs" / "agent-tool-requests.jsonl"
            state_dir = root / "state"

            payload_file.write_text(payload, encoding="utf-8")

            cmd = [
                sys.executable,
                str(MONITOR),
                "dev",
                "unit_test",
                str(payload_file),
                str(latest_file),
                str(events_file),
                str(tool_md_file),
                str(tool_events_file),
                str(state_dir),
            ]

            first = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            second = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(second.returncode, 0, msg=second.stderr)

            latest = json.loads(latest_file.read_text(encoding="utf-8"))
            self.assertIn("roles", latest)
            self.assertIn("dev", latest["roles"])
            self.assertEqual(latest["roles"]["dev"]["tool_request"], "shellcheck")
            self.assertEqual(latest["summary"]["tool_skill_requests_open"], 1)

            events = [line for line in events_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(events), 2)

            tool_lines = tool_md_file.read_text(encoding="utf-8").splitlines()
            request_lines = [line for line in tool_lines if line.startswith("- [") and "[dev]" in line]
            self.assertEqual(len(request_lines), 1)


if __name__ == "__main__":
    unittest.main()
