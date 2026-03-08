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

MODULE_PATH = AUTOMATION_DIR / "worker_manager.py"
SPEC = importlib.util.spec_from_file_location("fc_worker_manager", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_worker_manager"] = MODULE
SPEC.loader.exec_module(MODULE)


WorkerRecord = MODULE.WorkerRecord
_load_config = MODULE._load_config
_openclaw_capability_workspace = MODULE._openclaw_capability_workspace
_worker_prompt = MODULE._worker_prompt
_worker_runtime_model = MODULE._worker_runtime_model
plan_worker = MODULE.plan_worker
run_worker = MODULE.run_worker
collect_worker = MODULE.collect_worker
cleanup_workers = MODULE.cleanup_workers
status_snapshot = MODULE.status_snapshot
_save_registry = MODULE._save_registry


class WorkerManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        skills_root = self.root / "skills"
        for skill_name in ("browser-smoke", "repo-scan", "runtime-triage", "delivery-proof-check"):
            skill_dir = skills_root / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
        (self.root / "docs" / "operations" / "orchestrator").mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps(
                {
                    "version": "v1",
                    "defaults": {"prompt_timeout_seconds": 210, "retry_prompt_timeout_seconds": 90, "tick_timeout_seconds": 540},
                    "roles": {"planner": {}, "dev": {}, "admin": {}, "scrum_master": {}},
                    "features": {
                        "dynamic_workers": {
                            "enabled": 1,
                            "max_active": 3,
                            "default_ttl_min": 30,
                            "retry_max": 2,
                            "allowed_roles": ["planner", "dev", "admin"],
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

    def test_plan_allows_planner_repo_scan(self) -> None:
        result = plan_worker(self.config, "planner", "repo_scan_worker", "BATCH-11-PLAN", "repo_scan")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["result_kind"], "investigation_result")

    def test_plan_allows_planner_qa_review(self) -> None:
        result = plan_worker(self.config, "planner", "qa_review_worker", "BATCH-28-DEV-01", "qa_review")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["result_kind"], "qa_fix_result")

    def test_plan_refuses_scrum_master(self) -> None:
        result = plan_worker(self.config, "scrum_master", "repo_scan_worker", "BATCH-11-SM", "repo_scan")
        self.assertFalse(result["allowed"])
        self.assertIn("role_", result["reason"])

    def test_duplicate_guard_blocks_same_active_tuple(self) -> None:
        record = WorkerRecord(
            worker_id="worker_repo_scan_dup",
            worker_type="repo_scan_worker",
            parent_role="planner",
            owner_task_id="BATCH-11-PLAN",
            task_kind="repo_scan",
            status="running",
            created_at="2026-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
        )
        _save_registry(self.config.registry_path, [record])
        result = plan_worker(self.config, "planner", "repo_scan_worker", "BATCH-11-PLAN", "repo_scan")
        self.assertFalse(result["allowed"])
        self.assertIn("duplicate_active", result["reason"])

    def test_run_collect_and_merge_mock_worker(self) -> None:
        rc, payload = run_worker(
            self.config,
            role="dev",
            worker_type="test_worker",
            owner_task_id="BATCH-27-DEV-01",
            task_kind="targeted_test",
            message="Run targeted regression tests for dashboard summary.",
            ttl_min=15,
            backend="mock",
            timeout_seconds=120,
            thinking="medium",
            result_kind="test_result",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        worker_id = payload["worker_id"]

        rc_collect, collected = collect_worker(self.config, "dev", worker_id, "", mark_merged=True)
        self.assertEqual(rc_collect, 0)
        self.assertEqual(collected["worker_id"], worker_id)

        snapshot = status_snapshot(self.config, "dev")
        self.assertEqual(snapshot["active_count"], 0)
        self.assertTrue(any(item["worker_id"] == worker_id for item in snapshot["recent"]))

    def test_cleanup_removes_expired_worker(self) -> None:
        record = WorkerRecord(
            worker_id="worker_expired_01",
            worker_type="runtime_diag_worker",
            parent_role="admin",
            owner_task_id="BATCH-31-ADMIN-01",
            task_kind="runtime_diag",
            status="completed",
            created_at="2026-03-06T12:00:00Z",
            expires_at="2026-03-06T12:05:00Z",
            ttl_min=5,
            backend="mock",
        )
        _save_registry(self.config.registry_path, [record])
        cleaned = cleanup_workers(self.config)
        self.assertTrue(cleaned["ok"])
        self.assertIn("worker_expired_01", cleaned["removed"])

    def test_openclaw_capability_workspace_writes_minimal_codex_config(self) -> None:
        for relative in ("apps", "platform", "scripts", "docs", "data", "tests", "memory"):
            target = self.root / relative
            target.mkdir(parents=True, exist_ok=True)
        workspace = _openclaw_capability_workspace(self.root, "planner-dev", "gpt-5.4", "high")
        config_path = workspace / ".codex" / "config.toml"
        self.assertTrue(config_path.exists())
        body = config_path.read_text(encoding="utf-8")
        self.assertIn('model = "gpt-5.4"', body)
        self.assertIn('model_reasoning_effort = "high"', body)
        self.assertIn("[features]", body)
        self.assertNotIn("[agents]", body)
        self.assertIn("bounded planner-owned capability executor", (workspace / "SOUL.md").read_text(encoding="utf-8"))
        self.assertIn("Codex native multi-agent helpers", (workspace / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("real project tree is available via `./repo`", (workspace / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertFalse((workspace / "BOOTSTRAP.md").exists())
        for skill_name in ("browser-smoke", "repo-scan", "runtime-triage", "delivery-proof-check"):
            target = workspace / "skills" / skill_name
            self.assertTrue(target.is_symlink(), target)
        self.assertTrue((workspace / "repo").is_symlink())
        for relative in ("apps", "platform", "scripts", "docs", "data", "tests", "memory"):
            self.assertTrue((workspace / relative).is_symlink(), relative)
        self.assertIn("thin shell around the real project tree", (workspace / "WORKSPACE_MAP.md").read_text(encoding="utf-8"))

    def test_qa_worker_uses_full_model_and_fix_prompt(self) -> None:
        self.assertEqual(_worker_runtime_model("qa_review_worker"), "codex-full/gpt-5.4")
        prompt = _worker_prompt("qa_review_worker", "BATCH-28-DEV-01", "qa_review", "Check and fix API contract drift.")
        self.assertIn("allowed to resolve the issues you discover", prompt)
        self.assertIn("Preserve the existing frontend theme", prompt)


if __name__ == "__main__":
    unittest.main()
