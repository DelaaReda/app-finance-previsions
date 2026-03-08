from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "planner_subagent_manager.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_subagent_manager", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_subagent_manager"] = MODULE
SPEC.loader.exec_module(MODULE)


PlannerSubagentRecord = MODULE.PlannerSubagentRecord
_load_config = MODULE._load_config
_build_prompt = MODULE._build_prompt
plan_subagent = MODULE.plan_subagent
run_subagent = MODULE.run_subagent
collect_subagent = MODULE.collect_subagent
cleanup_subagents = MODULE.cleanup_subagents
status_snapshot = MODULE.status_snapshot
_save_registry = MODULE._save_registry


class PlannerSubagentManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "operations" / "orchestrator").mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps(
                {
                    "version": "v1",
                    "defaults": {"prompt_timeout_seconds": 210, "retry_prompt_timeout_seconds": 90, "tick_timeout_seconds": 540},
                    "roles": {
                        "planner": {"model": "gpt-5.4", "thinking": "high"},
                        "dev": {"model": "gpt-5.4", "thinking": "high"},
                        "admin": {"model": "gpt-5.4", "thinking": "medium"},
                        "scrum_master": {"model": "gpt-5.3-codex-spark", "thinking": "low"},
                    },
                    "features": {
                        "planner_orchestrator": {
                            "enabled": 1,
                            "cron_planner_only": 1,
                            "max_active": 2,
                            "default_ttl_min": 30,
                            "retry_max": 2,
                            "backend": "mock",
                            "managed_roles": ["dev", "admin", "scrum_master"],
                        }
                    },
                    "paths": {},
                    "timeouts": {},
                    "retries": {},
                    "telemetry": {},
                }
            ),
            encoding="utf-8",
        )
        self.config = _load_config(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_plan_allows_planner_to_spawn_dev(self) -> None:
        result = plan_subagent(self.config, "planner", "dev", "BATCH-61-DEV-01", "delivery")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["target_role"], "dev")

    def test_plan_refuses_non_planner_parent(self) -> None:
        result = plan_subagent(self.config, "admin", "dev", "BATCH-61-DEV-01", "delivery")
        self.assertFalse(result["allowed"])
        self.assertIn("parent_role_forbidden", result["reason"])

    def test_prompt_mentions_native_codex_multi_agent_helpers(self) -> None:
        prompt = _build_prompt("admin", "BATCH-61-ADMIN-01", "runtime", "Validate runtime truth.")
        self.assertIn("Codex native multi-agent helpers", prompt)
        self.assertIn("`monitor`", prompt)

    def test_duplicate_guard_blocks_same_target_and_task(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_dup",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-01",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="mock",
            last_update_at="2099-03-06T12:00:00Z",
        )
        _save_registry(self.config.registry_path, [record])
        result = plan_subagent(self.config, "planner", "dev", "BATCH-61-DEV-01", "delivery")
        self.assertFalse(result["allowed"])
        self.assertIn("duplicate_active", result["reason"])

    def test_run_collect_and_merge_mock_subagent(self) -> None:
        rc, payload = run_subagent(
            self.config,
            role="planner",
            target_role="admin",
            owner_task_id="BATCH-61-ADMIN-01",
            task_kind="runtime",
            message="Repair stale runtime blocker and return verification.",
            ttl_min=15,
            backend="mock",
            timeout_seconds=120,
        )
        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        subagent_id = payload["subagent_id"]

        rc_collect, collected = collect_subagent(self.config, "planner", subagent_id, "", mark_merged=True)
        self.assertEqual(rc_collect, 0)
        self.assertEqual(collected["subagent_id"], subagent_id)

        snapshot = status_snapshot(self.config, "planner")
        self.assertEqual(snapshot["active_count"], 0)
        self.assertTrue(any(item["subagent_id"] == subagent_id for item in snapshot["recent"]))

    def test_cleanup_removes_expired_subagent(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_scrum_expired",
            target_role="scrum_master",
            owner_task_id="BATCH-61-SM-01",
            parent_role="planner",
            task_kind="flow",
            status="completed",
            created_at="2026-03-06T12:00:00Z",
            expires_at="2026-03-06T12:05:00Z",
            ttl_min=5,
            backend="mock",
        )
        _save_registry(self.config.registry_path, [record])
        cleaned = cleanup_subagents(self.config)
        self.assertTrue(cleaned["ok"])
        self.assertIn("planner_scrum_expired", cleaned["removed"])

    def test_cleanup_removes_stale_running_subagent_without_result(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_stale",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-99",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2026-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="codex_exec",
            last_update_at="2026-03-06T12:00:00Z",
        )
        _save_registry(self.config.registry_path, [record])
        cleaned = cleanup_subagents(self.config)
        self.assertTrue(cleaned["ok"])
        self.assertIn("planner_dev_stale", cleaned["removed"])

    def test_cleanup_removes_missing_openclaw_agent_immediately(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_missing",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-98",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="openclaw",
            last_update_at="2099-03-06T12:00:00Z",
        )
        _save_registry(self.config.registry_path, [record])
        with patch.object(MODULE, "_openclaw_agent_ids", return_value=set()):
            cleaned = cleanup_subagents(self.config)
        self.assertTrue(cleaned["ok"])
        self.assertIn("planner_dev_missing", cleaned["removed"])

    def test_plan_refuses_openclaw_backend_when_binary_missing(self) -> None:
        with patch.object(MODULE, "_openclaw_available", return_value=False):
            result = plan_subagent(
                self.config,
                "planner",
                "dev",
                "BATCH-61-DEV-02",
                "delivery",
                backend_override="openclaw",
            )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "openclaw_missing")

    def test_run_openclaw_backend_extracts_structured_result(self) -> None:
        envelope = {
            "agent_id": "planner_dev_openclaw",
            "response": {
                "text": json.dumps(
                    {
                        "status": "completed",
                        "summary": "OpenClaw dev subagent completed targeted patch verification",
                        "artifact": "logs/openclaw/dev.result.json",
                        "verify": "proof=openclaw",
                        "files_touched": "src/app.py",
                        "tests_run": "pytest tests/test_app.py -q",
                        "recommended_next": "planner_merge_result",
                        "blocking_issue": "none",
                    }
                )
            },
        }

        with (
            patch.object(MODULE, "_openclaw_available", return_value=True),
            patch.object(MODULE, "_ensure_openclaw_agent", return_value=(True, "planner_dev_openclaw")),
            patch.object(
                MODULE.subprocess,
                "run",
                return_value=type(
                    "CompletedProcess",
                    (),
                    {"returncode": 0, "stdout": json.dumps(envelope), "stderr": ""},
                )(),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-02",
                task_kind="delivery",
                message="Apply a minimal fix and return structured evidence.",
                ttl_min=15,
                backend="openclaw",
                timeout_seconds=120,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "openclaw")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["artifact"], "logs/openclaw/dev.result.json")
        self.assertEqual(payload["tests_run"], "pytest tests/test_app.py -q")

    def test_run_openclaw_dev_uses_capability_workspace_and_writable_backend(self) -> None:
        captured: dict[str, object] = {}

        def _fake_ensure(agent_id, root, model, workspace_key="shared", thinking="medium", workspace_path=None):
            captured["agent_id"] = agent_id
            captured["root"] = root
            captured["model"] = model
            captured["workspace_key"] = workspace_key
            captured["thinking"] = thinking
            captured["workspace_path"] = workspace_path
            return True, "planner_dev_openclaw"

        envelope = {"response": {"text": json.dumps({"status": "completed", "summary": "ok", "artifact": "artifact.txt", "verify": "proof=openclaw", "files_touched": "x.py", "tests_run": "pytest -q", "commit_sha": "abc1234", "architecture_check": "layer=api", "vision_alignment": "batch=BATCH-61", "recommended_next": "planner_merge", "blocking_issue": "none"})}}
        with (
            patch.object(MODULE, "_openclaw_available", return_value=True),
            patch.object(MODULE, "_ensure_openclaw_agent", side_effect=_fake_ensure),
            patch.object(
                MODULE.subprocess,
                "run",
                return_value=type(
                    "CompletedProcess",
                    (),
                    {"returncode": 0, "stdout": json.dumps(envelope), "stderr": ""},
                )(),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-09",
                task_kind="delivery",
                message="Apply a minimal backend fix.",
                ttl_min=15,
                backend="openclaw",
                timeout_seconds=120,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(captured["model"], "codex-cli-write/gpt-5.4")
        self.assertIsNone(captured["workspace_path"])
        self.assertEqual(captured["workspace_key"], "planner-dev")

    def test_run_openclaw_backend_parses_embedded_final_json(self) -> None:
        embedded = (
            "progress line 1\n"
            "progress line 2\n"
            '{"status":"blocked","summary":"need writable sandbox","artifact":"none","verify":"none","files_touched":"none","tests_run":"SKIP(no_tests)","commit_sha":"none","architecture_check":"none","vision_alignment":"none","recommended_next":"rerun with writable backend","blocking_issue":"read_only_sandbox"}'
        )
        envelope = {"result": {"payloads": [{"text": embedded}]}}
        with (
            patch.object(MODULE, "_openclaw_available", return_value=True),
            patch.object(MODULE, "_ensure_openclaw_agent", return_value=(True, "planner_dev_openclaw")),
            patch.object(
                MODULE.subprocess,
                "run",
                return_value=type(
                    "CompletedProcess",
                    (),
                    {"returncode": 0, "stdout": json.dumps(envelope), "stderr": ""},
                )(),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-03",
                task_kind="delivery",
                message="Return the final embedded JSON only.",
                ttl_min=15,
                backend="openclaw",
                timeout_seconds=120,
            )

        self.assertEqual(rc, 6)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["blocking_issue"], "read_only_sandbox")

    def test_run_codex_exec_timeout_returns_failed_payload(self) -> None:
        timeout = subprocess.TimeoutExpired(cmd=["codex", "exec"], timeout=30)
        with (
            patch.object(MODULE, "_openclaw_agent_ids", return_value=set()),
            patch.object(MODULE.subprocess, "run", side_effect=timeout),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-04",
                task_kind="delivery",
                message="Timeout path",
                ttl_min=15,
                backend="codex_exec",
                timeout_seconds=30,
            )

        self.assertEqual(rc, 6)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("timeout", payload["blocking_issue"])


if __name__ == "__main__":
    unittest.main()
