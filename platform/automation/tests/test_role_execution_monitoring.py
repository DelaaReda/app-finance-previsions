#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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

    def test_flags_delivery_probe_loop_in_summary(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DELIVERY_PROBE_INCONSISTENT_CONTINUE",
                (
                    "EVIDENCE: exec_report=delivery_probe_inconsistent_lock_only; issues=none; suggestions=resume_delivery; "
                    "stream_id=BATCH-02; task_id=BATCH-02-BACKEND; tool_request=none; skill_request=none; "
                    "channels_read=runtime_context; impact_assessment=low; impact_action=resume_delivery"
                ),
                "RISKS: none",
                "NEXT: owner=backend_engineer; action=executer_cmd_metier_reel_puis_complete",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: RECHECK_DELIVERY_PROBE_BACKEND_ENGINEER_UTEST",
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
                "backend_engineer",
                "unit_test",
                str(payload_file),
                str(latest_file),
                str(events_file),
                str(tool_md_file),
                str(tool_events_file),
                str(state_dir),
            ]

            run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads(latest_file.read_text(encoding="utf-8"))
            self.assertEqual(latest["summary"]["delivery_probe_loops_open"], 1)
            self.assertIn("backend_engineer", latest["summary"]["delivery_probe_roles"])
            self.assertIn("backend_engineer", latest["summary"]["process_issue_roles"])

    def test_stale_context_records_are_excluded_from_active_issue_counts(self) -> None:
        payload = "\n".join(
            [
                "STATUS: EN_ATTENTE",
                "DELTA: NO_SLOT_BACKEND_ON_READY_BATCH02",
                (
                    "EVIDENCE: exec_report=no_slot_backend_actif; issues=no_slot_backend_sur_batch_ready; suggestions=assign_slot; "
                    "stream_id=BATCH-02; task_id=BATCH-02-BACKEND; tool_request=none; skill_request=none; "
                    "channels_read=workboard_tasks; impact_assessment=low; impact_action=monitor_updates; "
                    "queue_version=queue_123_olddeadbeef; workboard_version=workboard_123_olddeadbeef"
                ),
                "RISKS: none",
                "NEXT: owner=scrum_master; action=assign_slot_backend",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: BACKEND_SLOT_RECHECK_UTEST",
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
            queue_file = root / "docs" / "priority-queue.json"
            workboard_file = root / "docs" / "parallel-workstreams.json"

            queue_file.parent.mkdir(parents=True, exist_ok=True)
            queue_file.write_text('{"items":[]}\n', encoding="utf-8")
            workboard_file.write_text('{"tasks":[]}\n', encoding="utf-8")
            payload_file.write_text(payload, encoding="utf-8")

            cmd = [
                sys.executable,
                str(MONITOR),
                "backend_engineer",
                "unit_test",
                str(payload_file),
                str(latest_file),
                str(events_file),
                str(tool_md_file),
                str(tool_events_file),
                str(state_dir),
            ]
            env = os.environ.copy()
            env["EXEC_MONITOR_QUEUE_FILE"] = str(queue_file)
            env["EXEC_MONITOR_WORKBOARD_FILE"] = str(workboard_file)

            run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False, env=env)
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads(latest_file.read_text(encoding="utf-8"))
            self.assertEqual(latest["summary"]["stale_context_open"], 1)
            self.assertEqual(latest["summary"]["issues_open"], 0)
            self.assertIn("backend_engineer", latest["summary"]["stale_context_roles"])


if __name__ == "__main__":
    unittest.main()
