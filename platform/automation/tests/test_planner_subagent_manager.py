from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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

    def test_duplicate_guard_blocks_same_target_and_task(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_dup",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-01",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2026-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="mock",
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


if __name__ == "__main__":
    unittest.main()
