#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / "automation" / "role_execution_monitoring.py"


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

    def test_issue_reporting_fields_are_persisted_and_summarized(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: DEV_RUNTIME_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; exec_report=runtime_block_confirmed; "
                    "issues=agent_rate_limit_codex,upstream_timeout; issue_count=2; issue_severity=high; "
                    "suggestions=wait_and_retry; stream_id=BATCH-26; task_id=BATCH-26-DEV-02; "
                    "tool_request=none; skill_request=none; channels_read=workboard_tasks; "
                    "impact_assessment=high; impact_action=sync_cross_role"
                ),
                "RISKS: runtime blocked",
                "NEXT: owner=admin; action=retry after cooldown",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: AGENT_RATE_LIMIT_CODEX",
                "NEXT_ACTION_UNIQUE: DEV_ISSUE_REPORT_MONITOR_UTEST",
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

            run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            latest = json.loads(latest_file.read_text(encoding="utf-8"))
            dev = latest["roles"]["dev"]
            self.assertEqual(dev["issues"], "agent_rate_limit_codex,upstream_timeout")
            self.assertEqual(dev["issue_count"], 2)
            self.assertEqual(dev["issue_severity"], "high")
            self.assertTrue(dev["issue_reporting_ok"])
            self.assertEqual(latest["summary"]["issue_reports_open"], 1)
            self.assertEqual(latest["summary"]["issue_reporting_missing_count"], 0)

            rows = [
                json.loads(line)
                for line in events_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["issue_count"], 2)
            self.assertEqual(rows[0]["issue_severity"], "high")
            self.assertEqual(rows[0]["issue_codes"], ["agent_rate_limit_codex", "upstream_timeout"])

    def test_monitor_status_and_iteration_issues_include_issue_reporting(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        server_path = repo_root / "apps" / "monitor" / "server.py"
        import types

        added_modules: list[str] = []
        if "fastapi" not in sys.modules:
            fake_fastapi = types.ModuleType("fastapi")

            class _FakeFastAPI:  # noqa: N801
                def __init__(self, *args, **kwargs):
                    pass

                def add_middleware(self, *args, **kwargs):
                    return None

                def get(self, *args, **kwargs):
                    def decorator(func):
                        return func

                    return decorator

            fake_fastapi.FastAPI = _FakeFastAPI
            sys.modules["fastapi"] = fake_fastapi
            added_modules.append("fastapi")
        if "fastapi.middleware.cors" not in sys.modules:
            fake_cors = types.ModuleType("fastapi.middleware.cors")
            fake_cors.CORSMiddleware = object
            sys.modules["fastapi.middleware.cors"] = fake_cors
            added_modules.append("fastapi.middleware.cors")
        if "fastapi.responses" not in sys.modules:
            fake_resp = types.ModuleType("fastapi.responses")

            class _FakeJSONResponse(dict):  # noqa: N801
                def __init__(self, content=None, status_code=200, media_type=None):
                    super().__init__(content or {})
                    self.status_code = status_code
                    self.media_type = media_type

            fake_resp.HTMLResponse = object
            fake_resp.JSONResponse = _FakeJSONResponse
            sys.modules["fastapi.responses"] = fake_resp
            added_modules.append("fastapi.responses")
        if "uvicorn" not in sys.modules:
            fake_uvicorn = types.ModuleType("uvicorn")
            fake_uvicorn.run = lambda *args, **kwargs: None
            sys.modules["uvicorn"] = fake_uvicorn
            added_modules.append("uvicorn")

        spec = importlib.util.spec_from_file_location("fc_monitor_server_issue_test", server_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        self.assertIsNotNone(spec.loader)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        finally:
            for name in added_modules:
                sys.modules.pop(name, None)

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "docs" / "operations" / "orchestrator"
            logs = workspace / "logs-codex-runs" / "executor-monitoring"
            orch.mkdir(parents=True, exist_ok=True)
            logs.mkdir(parents=True, exist_ok=True)

            latest = {
                "roles": {
                    "planner": {"issue_count": 0, "issue_severity": "none", "issue_reporting_ok": True},
                    "dev": {"issue_count": 2, "issue_severity": "critical", "issue_reporting_ok": True},
                    "admin": {"issue_count": 0, "issue_severity": "none", "issue_reporting_ok": False},
                }
            }
            (orch / "executors-monitoring-latest.json").write_text(
                json.dumps(latest) + "\n",
                encoding="utf-8",
            )
            now_dt = datetime.now(timezone.utc)
            events_rows = [
                {
                    "ts_utc": (now_dt.replace(microsecond=0)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "role": "dev",
                    "task_id": "BATCH-26-DEV-02",
                    "stream_id": "BATCH-26",
                    "status": "BLOCKED",
                    "delta": "DEV_RUNTIME_BLOCK",
                    "blocker_id": "AGENT_RATE_LIMIT_CODEX",
                    "issues": "agent_rate_limit_codex,upstream_timeout",
                    "issue_codes": ["agent_rate_limit_codex", "upstream_timeout"],
                    "issue_count": 2,
                    "issue_severity": "critical",
                    "issue_reporting_ok": True,
                    "issue_reporting_errors": [],
                    "next_action_unique": "DEV_FIX_1",
                    "source": "unit_test",
                },
                {
                    "ts_utc": (now_dt.replace(microsecond=0)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "role": "admin",
                    "task_id": "BATCH-26-ADMIN-01",
                    "stream_id": "BATCH-26",
                    "status": "IN_PROGRESS",
                    "delta": "NO_DELTA",
                    "blocker_id": "NONE",
                    "issues": "none",
                    "issue_codes": [],
                    "issue_count": 0,
                    "issue_severity": "none",
                    "issue_reporting_ok": False,
                    "issue_reporting_errors": ["issue_count_missing"],
                    "next_action_unique": "ADMIN_FIX_1",
                    "source": "unit_test",
                },
            ]
            events_file = logs / "events.jsonl"
            events_file.write_text(
                "\n".join(json.dumps(row) for row in events_rows) + "\n",
                encoding="utf-8",
            )

            previous_root = module.ROOT
            previous_events = module.ITERATION_EVENTS_FILE
            previous_discover = module.discover_roles
            try:
                module.ROOT = workspace
                module.ITERATION_EVENTS_FILE = events_file
                module.discover_roles = lambda: ("planner", "dev", "admin")

                status_payload = module.status()
                self.assertIn("issue_reporting", status_payload)
                self.assertEqual(status_payload["issue_reporting"]["roles_total"], 3)
                self.assertEqual(status_payload["issue_reporting"]["reports_with_issues"], 1)
                self.assertEqual(status_payload["issue_reporting"]["critical_count"], 1)
                self.assertIn("admin", status_payload["issue_reporting"]["roles_missing_report"])

                issues_payload = module.iteration_issues(role="dev", severity="critical", recent_minutes=1440, n=20)
                self.assertEqual(issues_payload["count"], 1)
                self.assertEqual(issues_payload["items"][0]["role"], "dev")
                self.assertEqual(issues_payload["items"][0]["issue_severity"], "critical")
            finally:
                module.ROOT = previous_root
                module.ITERATION_EVENTS_FILE = previous_events
                module.discover_roles = previous_discover

    def test_monitor_planner_autonomy_snapshot_counts_recent_autofix(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        server_path = repo_root / "apps" / "monitor" / "server.py"
        import types

        added_modules: list[str] = []
        if "fastapi" not in sys.modules:
            fake_fastapi = types.ModuleType("fastapi")

            class _FakeFastAPI:  # noqa: N801
                def __init__(self, *args, **kwargs):
                    pass

                def add_middleware(self, *args, **kwargs):
                    return None

                def get(self, *args, **kwargs):
                    def decorator(func):
                        return func

                    return decorator

            fake_fastapi.FastAPI = _FakeFastAPI
            sys.modules["fastapi"] = fake_fastapi
            added_modules.append("fastapi")
        if "fastapi.middleware.cors" not in sys.modules:
            fake_cors = types.ModuleType("fastapi.middleware.cors")
            fake_cors.CORSMiddleware = object
            sys.modules["fastapi.middleware.cors"] = fake_cors
            added_modules.append("fastapi.middleware.cors")
        if "fastapi.responses" not in sys.modules:
            fake_resp = types.ModuleType("fastapi.responses")
            fake_resp.HTMLResponse = object
            fake_resp.JSONResponse = object
            sys.modules["fastapi.responses"] = fake_resp
            added_modules.append("fastapi.responses")
        if "uvicorn" not in sys.modules:
            fake_uvicorn = types.ModuleType("uvicorn")
            fake_uvicorn.run = lambda *args, **kwargs: None
            sys.modules["uvicorn"] = fake_uvicorn
            added_modules.append("uvicorn")

        spec = importlib.util.spec_from_file_location("fc_monitor_server_test", server_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        self.assertIsNotNone(spec.loader)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        finally:
            for name in added_modules:
                sys.modules.pop(name, None)

        now_ts = datetime(2026, 3, 3, 18, 0, 0, tzinfo=timezone.utc).timestamp()
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            orch = workspace / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "planner-guardian-latest.json").write_text(
                json.dumps(
                    {
                        "ready_idle_streak": 2,
                        "low_score_streak": 1,
                        "runway_no_batch_streak": 3,
                    }
                ),
                encoding="utf-8",
            )
            (orch / "planner-guardian-events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "ts_utc": "2026-03-03T12:00:00Z",
                                "event": "planner_soft_autofix",
                                "reason": "normalized_handoff_to_dev",
                                "autofix_applied": True,
                            }
                        ),
                        json.dumps(
                            {
                                "ts_utc": "2026-03-01T08:00:00Z",
                                "event": "planner_soft_autofix",
                                "reason": "old_event_outside_window",
                                "autofix_applied": True,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            previous_root = module.ROOT
            try:
                module.ROOT = workspace
                snap = module.planner_autonomy_snapshot(now_ts=now_ts)
            finally:
                module.ROOT = previous_root

            self.assertEqual(snap["ready_idle_streak"], 2)
            self.assertEqual(snap["low_score_streak"], 1)
            self.assertEqual(snap["runway_no_batch_streak"], 3)
            self.assertEqual(snap["autofix_count_24h"], 1)
            self.assertIn("normalized_handoff_to_dev", snap["last_autofix_reason"])


if __name__ == "__main__":
    unittest.main()
