from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

if "yaml" not in sys.modules:
    fake_yaml = types.ModuleType("yaml")
    fake_yaml.safe_load = lambda *args, **kwargs: {}
    fake_yaml.safe_dump = lambda *args, **kwargs: ""
    sys.modules["yaml"] = fake_yaml

from runtime.truth.event_store import EventStore

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
_canonical_runtime_root = MODULE._canonical_runtime_root
_runtime_relpath = MODULE._runtime_relpath


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
                        "admin": {"model": "gpt-5.4", "thinking": "high"},
                        "scrum_master": {"model": "gpt-5.4", "thinking": "high"},
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

    def test_plan_rejects_owner_task_target_role_mismatch(self) -> None:
        result = plan_subagent(self.config, "planner", "admin", "BATCH-61-DEV-02", "runtime")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "owner_task_target_role_mismatch:dev!=admin")

    def test_prompt_enforces_json_only_contract_and_narrow_scope_rule(self) -> None:
        prompt = _build_prompt("admin", "BATCH-61-ADMIN-01", "runtime", "Validate runtime truth.")
        self.assertIn("Hard output contract:", prompt)
        self.assertIn("Return exactly one JSON object only:", prompt)
        self.assertIn("No markdown, no code fence, no prose before or after", prompt)
        self.assertIn("status must be completed, blocked, or failed.", prompt)
        self.assertIn("Work on the narrowest file/test set that can unblock OWNER_TASK_ID", prompt)
        self.assertIn("for large memory/log files use rg/sed/tail instead of cat.", prompt)
        self.assertIn("Prefer a bounded fix or artifact now; do not stop at analysis-only", prompt)
        self.assertIn("no kickoff/progress chatter or shell/banner echo", prompt)
        self.assertIn("Finance Copilot brief+ask with explainable memo output", prompt)
        self.assertIn("queue/workboard/monitor are projections", prompt)
        self.assertIn("planner_runtime_actions.py, runtime truth helpers, VM-safe wrappers", prompt)
        self.assertIn("recommended_next=planner_route_to_dev_or_scrum", prompt)

    def test_config_defaults_to_native_codex_runtime_policy(self) -> None:
        self.assertFalse(self.config.allow_runtime_explorer)
        self.assertEqual(self.config.default_helper_mode, "native_codex")

    def test_admin_runtime_uses_full_backend_sandbox(self) -> None:
        result = plan_subagent(self.config, "planner", "admin", "BATCH-61-ADMIN-01", "runtime")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["sandbox"], "danger-full-access")

    def test_backend_by_role_mapping_overrides_auto_backend(self) -> None:
        self.config.backend = "auto"
        self.config.backend_by_role = {"admin": "codex_exec", "dev": "openclaw"}
        with patch.object(MODULE, "shutil_which", return_value="/usr/bin/mock"):
            admin_result = plan_subagent(self.config, "planner", "admin", "BATCH-61-ADMIN-01", "runtime")
            dev_result = plan_subagent(self.config, "planner", "dev", "BATCH-61-DEV-01", "delivery")
        self.assertEqual(admin_result["backend"], "codex_exec")
        self.assertTrue(dev_result["allowed"])
        self.assertEqual(dev_result["backend"], "codex_exec")
        self.assertEqual(dev_result["provider_policy_plane"], "model_plane")

    def test_plan_rejects_qwen_as_primary_backend(self) -> None:
        self.config.backend_by_role = {"delivery": "qwen"}
        result = plan_subagent(self.config, "planner", "dev", "BATCH-61-DEV-04", "delivery")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "unsupported_backend:qwen")

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

    def test_duplicate_guard_ignores_running_record_with_collectible_result(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_collectible",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-03",
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
        self.config.results_dir.mkdir(parents=True, exist_ok=True)
        (self.config.results_dir / "planner_dev_collectible.result.json").write_text(
            json.dumps({"status": "completed", "artifact": "mock://artifact", "verify": "before=a; after=b; test=c"}),
            encoding="utf-8",
        )
        result = plan_subagent(self.config, "planner", "dev", "BATCH-61-DEV-03", "delivery")
        self.assertTrue(result["allowed"])

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
        graph_state = EventStore(self.root).load_graph_state("BATCH-61-ADMIN-01") or {}
        self.assertEqual(graph_state.get("status"), "merged")
        self.assertEqual(graph_state.get("current_node"), "close_or_requeue")

    def test_run_subagent_preserves_last_structured_json_when_startup_noise_is_present(self) -> None:
        self.config.backend = "codex_exec"
        self.config.enabled = True
        stdout = "\n".join(
            [
                "OpenAI Codex v0.114.0 (research preview)",
                '{"status":"in_progress","summary":"Taking ownership.","root_cause":"","fix_applied":"","artifact":"","verify":"","files_touched":"","tests_run":"","commit_sha":"","architecture_check":"","vision_alignment":"","recommended_next":"","blocking_issue":""}',
                '{"status":"in_progress","summary":"Patch failed due context drift; I will re-read the exact script block and apply a narrower update so only the personal-finance page override logic changes.","root_cause":"","fix_applied":"","artifact":"","verify":"","files_touched":"","tests_run":"","commit_sha":"","architecture_check":"","vision_alignment":"","recommended_next":"Re-run targeted tests after patch.","blocking_issue":"Patch context mismatch from prior file version."}',
            ]
        )
        stderr = "invalid_subagent_result:start_banner_only"

        with patch.object(MODULE, "shutil_which", return_value="/usr/bin/codex"), patch.object(
            MODULE,
            "_run_codex_exec_subagent",
            return_value=(0, stdout, stderr, "codex_exec:planner_dev_live"),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-90",
                task_kind="delivery",
                message="Implement the next slice and return proof.",
                ttl_min=15,
                backend="codex_exec",
                timeout_seconds=120,
                subagent_id_override="planner_dev_live",
            )

        self.assertEqual(rc, 6)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("Patch failed due context drift", payload["summary"])
        self.assertEqual(payload["blocking_issue"], "Patch context mismatch from prior file version.")
        self.assertEqual(payload["recommended_next"], "Re-run targeted tests after patch.")

    def test_value_present_rejects_placeholder_only_segments(self) -> None:
        self.assertFalse(MODULE._value_present("..."))
        self.assertFalse(MODULE._value_present("before=...; after=...; test=..."))
        self.assertFalse(MODULE._value_present("layer=...; imports_ok=...; path_target=..."))
        self.assertTrue(MODULE._value_present("before=500; after=200; test=pytest"))

    def test_run_subagent_records_running_graph_state_before_backend_returns(self) -> None:
        self.config.backend = "codex_exec"
        seen_state: dict[str, object] = {}

        def _fake_run(*args, **kwargs):
            payload = EventStore(self.root).load_graph_state("BATCH-61-ADMIN-02") or {}
            seen_state.update(payload)
            return (
                0,
                json.dumps(
                    {
                        "status": "completed",
                        "summary": "runtime repaired",
                        "root_cause": "stale monitor state",
                        "fix_applied": "doctor refresh",
                        "artifact": "logs/runtime-proof.txt",
                        "verify": "before=degraded; after=ok; test=doctor",
                        "files_touched": "platform/automation/fc_doctor.py",
                        "tests_run": "python3 -m pytest platform/automation/tests/test_fc_doctor.py",
                        "commit_sha": "abc123",
                        "architecture_check": "pass",
                        "vision_alignment": "pass",
                        "recommended_next": "none",
                        "blocking_issue": "none",
                    }
                ),
                "",
                "codex_exec:planner_admin_live",
            )

        with patch.object(MODULE, "shutil_which", return_value="/usr/bin/codex"), patch.object(
            MODULE, "_run_codex_exec_subagent", side_effect=_fake_run
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="admin",
                owner_task_id="BATCH-61-ADMIN-02",
                task_kind="runtime",
                message="Repair runtime and report proof.",
                ttl_min=15,
                backend="codex_exec",
                timeout_seconds=120,
                subagent_id_override="planner_admin_live",
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(seen_state.get("status"), "running")
        self.assertEqual(seen_state.get("current_node"), "wait_or_collect_result")
        self.assertEqual(seen_state.get("task_id"), "BATCH-61-ADMIN-02")
        final_state = EventStore(self.root).load_graph_state("BATCH-61-ADMIN-02") or {}
        self.assertEqual(final_state.get("status"), "ready_to_merge")
        self.assertEqual(final_state.get("target_role"), "admin")

    def test_collect_recovers_result_when_registry_row_is_missing(self) -> None:
        self.config.results_dir.mkdir(parents=True, exist_ok=True)
        (self.config.results_dir / "planner_dev_recovered.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_recovered",
                    "target_role": "dev",
                    "owner_task_id": "BATCH-61-DEV-77",
                    "parent_role": "planner",
                    "task_kind": "delivery",
                    "status": "completed",
                    "summary": "Recovered dev result",
                    "root_cause": "context drift",
                    "fix_applied": "connector normalized",
                    "artifact": "mock://artifact",
                    "verify": "before=a; after=b; test=c",
                    "files_touched": "app.js",
                    "tests_run": "SKIP(no_tests)",
                    "commit_sha": "abc123",
                    "architecture_check": "pass",
                    "vision_alignment": "pass",
                    "recommended_next": "none",
                    "blocking_issue": "none",
                }
            ),
            encoding="utf-8",
        )

        rc_collect, collected = collect_subagent(self.config, "planner", "", "BATCH-61-DEV-77", mark_merged=True)
        self.assertEqual(rc_collect, 0)
        self.assertTrue(collected["ok"])
        self.assertEqual(collected["subagent_id"], "planner_dev_recovered")

        snapshot = status_snapshot(self.config, "planner")
        recent = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_dev_recovered")
        self.assertEqual(recent["status"], "merged")

    def test_collect_prefers_explicit_subagent_id_over_stale_owner_task_match(self) -> None:
        stale_record = PlannerSubagentRecord(
            subagent_id="planner_dev_stale",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-77",
            parent_role="planner",
            task_kind="delivery",
            status="failed",
            created_at="2099-03-06T11:00:00Z",
            expires_at="2099-03-06T11:30:00Z",
            ttl_min=30,
            backend="codex_exec",
            last_update_at="2099-03-06T11:05:00Z",
            summary="stale owner-task match",
            blocking_issue="invalid_subagent_result:missing_result_payload",
        )
        _save_registry(self.config.registry_path, [stale_record])
        self.config.results_dir.mkdir(parents=True, exist_ok=True)
        (self.config.results_dir / "planner_dev_latest.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_latest",
                    "target_role": "dev",
                    "owner_task_id": "BATCH-61-DEV-77",
                    "parent_role": "planner",
                    "task_kind": "delivery",
                    "status": "failed",
                    "summary": "Latest explicit subagent result",
                    "root_cause": "codex_exec_rate_limit",
                    "fix_applied": "none",
                    "artifact": "logs/latest.json",
                    "verify": "rate_limit_window=active",
                    "files_touched": "none",
                    "tests_run": "SKIP(no_tests)",
                    "commit_sha": "none",
                    "architecture_check": "none",
                    "vision_alignment": "none",
                    "recommended_next": "wait_for_quota",
                    "blocking_issue": "codex_exec_rate_limit",
                }
            ),
            encoding="utf-8",
        )

        rc_collect, collected = collect_subagent(
            self.config,
            "planner",
            "planner_dev_latest",
            "BATCH-61-DEV-77",
            mark_merged=True,
        )

        self.assertEqual(rc_collect, 6)
        self.assertFalse(collected["ok"])
        self.assertEqual(collected["subagent_id"], "planner_dev_latest")
        self.assertEqual(collected["blocking_issue"], "codex_exec_rate_limit")

    def test_collect_accepts_complete_status_payload_as_success(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_complete",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-88",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="qwen",
            last_update_at="2099-03-06T12:00:00Z",
        )
        _save_registry(self.config.registry_path, [record])
        self.config.results_dir.mkdir(parents=True, exist_ok=True)
        (self.config.results_dir / "planner_dev_complete.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_complete",
                    "target_role": "dev",
                    "owner_task_id": "BATCH-61-DEV-88",
                    "parent_role": "planner",
                    "task_kind": "delivery",
                    "status": "complete",
                    "summary": "Delivered with proof via fallback backend",
                    "root_cause": "none",
                    "fix_applied": "normalized success token",
                    "artifact": "docs/proof.md",
                    "verify": "before=x; after=y; test=z",
                    "files_touched": "apps/api/src/example.py",
                    "tests_run": "pytest -q test_example.py",
                    "commit_sha": "abc123",
                    "architecture_check": "pass",
                    "vision_alignment": "pass",
                    "recommended_next": "none",
                    "blocking_issue": "none",
                }
            ),
            encoding="utf-8",
        )

        rc_collect, collected = collect_subagent(self.config, "planner", "planner_dev_complete", "", mark_merged=True)

        self.assertEqual(rc_collect, 0)
        self.assertTrue(collected["ok"])
        self.assertEqual(collected["status"], "complete")
        snapshot = status_snapshot(self.config, "planner")
        merged = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_dev_complete")
        self.assertEqual(merged["status"], "merged")

    def test_collect_accepts_failed_status_when_delivery_proof_is_complete(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_failed_with_proof",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-89",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="qwen",
            last_update_at="2099-03-06T12:00:00Z",
        )
        _save_registry(self.config.registry_path, [record])
        self.config.results_dir.mkdir(parents=True, exist_ok=True)
        (self.config.results_dir / "planner_dev_failed_with_proof.result.json").write_text(
            json.dumps(
                {
                    "subagent_id": "planner_dev_failed_with_proof",
                    "target_role": "dev",
                    "owner_task_id": "BATCH-61-DEV-89",
                    "parent_role": "planner",
                    "task_kind": "delivery",
                    "status": "failed",
                    "summary": "Delivery completed via fallback backend",
                    "root_cause": "backend fallback mislabeled the terminal status",
                    "fix_applied": "proof payload preserved",
                    "artifact": "docs/proof.md",
                    "verify": "before=x; after=y; test=z",
                    "files_touched": "apps/api/src/example.py",
                    "tests_run": "pytest -q test_example.py",
                    "commit_sha": "abc123",
                    "architecture_check": "pass",
                    "vision_alignment": "pass",
                    "recommended_next": "none",
                    "blocking_issue": "none",
                }
            ),
            encoding="utf-8",
        )

        rc_collect, collected = collect_subagent(
            self.config,
            "planner",
            "planner_dev_failed_with_proof",
            "",
            mark_merged=True,
        )

        self.assertEqual(rc_collect, 0)
        self.assertTrue(collected["ok"])
        snapshot = status_snapshot(self.config, "planner")
        merged = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_dev_failed_with_proof")
        self.assertEqual(merged["status"], "merged")

    def test_collect_keeps_active_subagent_running_when_result_payload_missing(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_pending",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-88",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="codex_exec",
            last_update_at="2099-03-06T12:05:00Z",
        )
        _save_registry(self.config.registry_path, [record])
        self.config.results_dir.mkdir(parents=True, exist_ok=True)

        rc_collect, collected = collect_subagent(self.config, "planner", "planner_dev_pending", "", mark_merged=True)
        self.assertNotEqual(rc_collect, 0)
        self.assertFalse(collected["ok"])
        self.assertEqual(collected["status"], "running")
        self.assertIn("subagent_result_pending:missing_result_payload", str(collected.get("blocking_issue", "")))

        snapshot = status_snapshot(self.config, "planner")
        active = next(item for item in snapshot["active"] if item["subagent_id"] == "planner_dev_pending")
        self.assertEqual(active["status"], "running")

    def test_status_snapshot_marks_qwen_backend_as_degraded(self) -> None:
        record = PlannerSubagentRecord(
            subagent_id="planner_dev_qwen",
            target_role="dev",
            owner_task_id="BATCH-61-DEV-09",
            parent_role="planner",
            task_kind="delivery",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="qwen",
            last_update_at="2099-03-06T12:05:00Z",
            metadata={
                "purpose": "delivery",
                "role": "dev",
                "last_meaningful_delta": "degraded_backend:qwen_fallback",
                "stalled": False,
            },
        )
        _save_registry(self.config.registry_path, [record])
        snapshot = status_snapshot(self.config, "planner")
        self.assertTrue(snapshot["degraded_backend"])
        self.assertEqual(snapshot["planner_state"], "degraded_backend")
        self.assertEqual(snapshot["latest_backend"], "qwen")
        self.assertEqual(snapshot["latest_last_meaningful_delta"], "degraded_backend:qwen_fallback")

    def test_save_registry_does_not_regress_merged_to_running(self) -> None:
        merged = PlannerSubagentRecord(
            subagent_id="planner_admin_merged",
            target_role="admin",
            owner_task_id="BATCH-61-ADMIN-03",
            parent_role="planner",
            task_kind="runtime",
            status="merged",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="codex_exec",
            last_update_at="2099-03-06T12:10:00Z",
            summary="merged summary",
            artifact="proof.json",
            verify="before=a; after=b; test=c",
            merged_at="2099-03-06T12:11:00Z",
        )
        stale_running = PlannerSubagentRecord(
            subagent_id="planner_admin_merged",
            target_role="admin",
            owner_task_id="BATCH-61-ADMIN-03",
            parent_role="planner",
            task_kind="runtime",
            status="running",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="codex_exec",
            last_update_at="2099-03-06T12:05:00Z",
        )
        _save_registry(self.config.registry_path, [merged])
        _save_registry(self.config.registry_path, [stale_running])
        snapshot = status_snapshot(self.config, "planner")
        recent = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_admin_merged")
        self.assertEqual(recent["status"], "merged")
        self.assertEqual(recent["artifact"], "proof.json")

    def test_run_subagent_triggers_bridge_collect(self) -> None:
        with patch.object(MODULE, "_trigger_runtime_collect") as collect_mock:
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="admin",
                owner_task_id="BATCH-61-ADMIN-04",
                task_kind="runtime",
                message="Repair blocker.",
                ttl_min=15,
                backend="mock",
                timeout_seconds=120,
            )
        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        collect_mock.assert_called_once()

    def test_collect_rejects_startup_banner_only_result(self) -> None:
        registry_path = self.config.registry_path
        results_dir = self.config.results_dir
        results_dir.mkdir(parents=True, exist_ok=True)
        record = PlannerSubagentRecord(
            subagent_id="planner_admin_banner",
            target_role="admin",
            owner_task_id="BATCH-61-ADMIN-02",
            parent_role="planner",
            task_kind="runtime",
            status="completed",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="openclaw",
            last_update_at="2099-03-06T12:05:00Z",
        )
        _save_registry(registry_path, [record])
        (results_dir / "planner_admin_banner.raw.txt").write_text(
            "OpenAI Codex v0.0\nReasoning effort: high\nfailed to refresh available models\n",
            encoding="utf-8",
        )
        rc_collect, collected = collect_subagent(self.config, "planner", "planner_admin_banner", "", mark_merged=True)
        self.assertNotEqual(rc_collect, 0)
        self.assertFalse(collected["ok"])
        self.assertFalse(collected["mergeable"])
        snapshot = status_snapshot(self.config, "planner")
        recent = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_admin_banner")
        self.assertEqual(recent["status"], "failed")

    def test_collect_rejects_auth_or_transport_noise(self) -> None:
        registry_path = self.config.registry_path
        results_dir = self.config.results_dir
        results_dir.mkdir(parents=True, exist_ok=True)
        record = PlannerSubagentRecord(
            subagent_id="planner_admin_auth",
            target_role="admin",
            owner_task_id="BATCH-61-ADMIN-05",
            parent_role="planner",
            task_kind="runtime",
            status="completed",
            created_at="2099-03-06T12:00:00Z",
            expires_at="2099-03-06T12:30:00Z",
            ttl_min=30,
            backend="openclaw",
            last_update_at="2099-03-06T12:05:00Z",
        )
        _save_registry(registry_path, [record])
        (results_dir / "planner_admin_auth.raw.txt").write_text(
            "worker quit with fatal: Transport channel closed\nunexpected status 401 Unauthorized\n",
            encoding="utf-8",
        )
        rc_collect, collected = collect_subagent(self.config, "planner", "planner_admin_auth", "", mark_merged=True)
        self.assertNotEqual(rc_collect, 0)
        self.assertFalse(collected["ok"])
        self.assertFalse(collected["mergeable"])
        self.assertIn("invalid_subagent_result", str(collected.get("blocking_issue", "")))
        snapshot = status_snapshot(self.config, "planner")
        recent = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_admin_auth")
        self.assertIn("invalid_subagent_result", recent["blocking_issue"])

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
        snapshot = status_snapshot(self.config, "planner")
        recent = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_dev_stale")
        self.assertEqual(recent["status"], "failed")
        self.assertIn("stale_active_no_result", recent["blocking_issue"])

    def test_cleanup_removes_legacy_openclaw_backend_immediately(self) -> None:
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
        cleaned = cleanup_subagents(self.config)
        self.assertTrue(cleaned["ok"])
        self.assertIn("planner_dev_missing", cleaned["removed"])
        snapshot = status_snapshot(self.config, "planner")
        recent = next(item for item in snapshot["recent"] if item["subagent_id"] == "planner_dev_missing")
        self.assertEqual(recent["status"], "failed")
        self.assertEqual(recent["blocking_issue"], "legacy_openclaw_backend_unsupported")

    def test_plan_refuses_openclaw_backend_when_binary_missing(self) -> None:
        with patch.object(MODULE, "shutil_which", side_effect=lambda binary: "" if binary == "openclaw" else "/usr/bin/mock"):
            result = plan_subagent(
                self.config,
                "planner",
                "dev",
                "BATCH-61-DEV-02",
                "delivery",
                backend_override="openclaw",
            )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["backend"], "codex_exec")
        self.assertEqual(result["provider_policy_plane"], "model_plane")

    def test_run_openclaw_backend_degrades_to_codex_exec_by_default(self) -> None:
        with (
            patch.object(
                MODULE,
                "_run_codex_exec_subagent",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "Codex exec handled deprecated openclaw backend",
                            "artifact": "logs/codex/dev.result.json",
                            "verify": "proof=codex_exec",
                            "files_touched": "src/app.py",
                            "tests_run": "pytest tests/test_app.py -q",
                            "recommended_next": "planner_merge_result",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_dev_openclaw:gpt-5.4",
                ),
            ) as codex_mock,
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
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")
        codex_mock.assert_called_once()

    def test_run_openclaw_dev_backend_stays_deprecated_even_when_env_enabled(self) -> None:
        with (
            patch.dict(os.environ, {"FC_ALLOW_OPENCLAW_SUBAGENT_PROVIDER": "1"}, clear=False),
            patch.object(
                MODULE,
                "_run_codex_exec_subagent",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "Codex exec handled deprecated openclaw backend",
                            "artifact": "logs/codex/dev.result.json",
                            "verify": "proof=codex_exec",
                            "files_touched": "src/app.py",
                            "tests_run": "pytest tests/test_app.py -q",
                            "recommended_next": "planner_merge_result",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_dev_openclaw:gpt-5.4",
                ),
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
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")

    def test_run_openclaw_admin_backend_stays_deprecated_even_when_env_enabled(self) -> None:
        with (
            patch.dict(os.environ, {"FC_ALLOW_OPENCLAW_SUBAGENT_PROVIDER": "1"}, clear=False),
            patch.object(
                MODULE,
                "_run_codex_exec_subagent",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "Codex exec handled deprecated openclaw backend",
                            "artifact": "logs/codex/admin.result.json",
                            "verify": "proof=codex_exec",
                            "files_touched": "src/runtime.py",
                            "tests_run": "pytest tests/test_runtime.py -q",
                            "recommended_next": "planner_merge_result",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_admin_openclaw:gpt-5.4",
                ),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="admin",
                owner_task_id="BATCH-61-ADMIN-09",
                task_kind="runtime",
                message="Repair runtime truth.",
                ttl_min=15,
                backend="openclaw",
                timeout_seconds=120,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")

    def test_run_openclaw_backend_never_reaches_provider_execution(self) -> None:
        with (
            patch.dict(os.environ, {"FC_ALLOW_OPENCLAW_SUBAGENT_PROVIDER": "1"}, clear=False),
            patch.object(
                MODULE,
                "_run_codex_exec_subagent",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "Codex exec handled deprecated openclaw backend",
                            "artifact": "logs/codex/dev.result.json",
                            "verify": "proof=codex_exec",
                            "files_touched": "src/app.py",
                            "tests_run": "pytest tests/test_app.py -q",
                            "recommended_next": "planner_merge_result",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_dev_openclaw:gpt-5.4",
                ),
            ) as codex_mock,
            patch.object(MODULE.subprocess, "run") as subprocess_mock,
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

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")
        codex_mock.assert_called_once()
        subprocess_mock.assert_not_called()

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

    def test_run_codex_exec_rate_limit_falls_back_to_qwen(self) -> None:
        def _fake_run(cmd, **kwargs):
            out_path = Path(cmd[cmd.index("-o") + 1])
            out_path.write_text("", encoding="utf-8")
            return type(
                "CompletedProcess",
                (),
                {"returncode": 1, "stdout": "", "stderr": "status 429 insufficient_quota"},
            )()

        with (
            patch.object(MODULE, "_openclaw_agent_ids", return_value=set()),
            patch.object(MODULE.subprocess, "run", side_effect=_fake_run),
            patch.object(
                MODULE,
                "model_plane_run_secondary_then_qwen_fallback",
                return_value=(0, json.dumps({"status": "completed", "summary": "qwen ok", "artifact": "artifact.txt", "verify": "proof=qwen", "files_touched": "x.py", "tests_run": "pytest -q", "commit_sha": "abc1234", "architecture_check": "layer=runtime", "vision_alignment": "batch=BATCH-61", "recommended_next": "planner_merge", "blocking_issue": "none"}), "", "qwen:planner_dev_qwen"),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-07",
                task_kind="delivery",
                message="Rate limit fallback path",
                ttl_min=15,
                backend="codex_exec",
                timeout_seconds=30,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "qwen")
        self.assertEqual(payload["backend_ref"], "qwen:planner_dev_qwen")
        self.assertEqual(payload["backend_route_reason"], "qwen_fallback")
        self.assertEqual(payload["model"], "qwen")

    def test_run_codex_exec_rate_limit_falls_back_to_secondary_codex_before_qwen(self) -> None:
        def _fake_run(cmd, **kwargs):
            out_path = Path(cmd[cmd.index("-o") + 1])
            out_path.write_text("", encoding="utf-8")
            return type(
                "CompletedProcess",
                (),
                {"returncode": 1, "stdout": "", "stderr": "You've hit your usage limit for GPT-5.3-Codex-Spark. Switch to another model now."},
            )()

        with (
            patch.object(MODULE, "_openclaw_agent_ids", return_value=set()),
            patch.object(MODULE.subprocess, "run", side_effect=_fake_run),
            patch.object(
                MODULE,
                "model_plane_run_secondary_then_qwen_fallback",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "secondary codex ok",
                            "artifact": "artifact.txt",
                            "verify": "proof=secondary",
                            "files_touched": "src/app.py",
                            "tests_run": "pytest -q",
                            "commit_sha": "abc1234",
                            "architecture_check": "layer=api",
                            "vision_alignment": "batch=BATCH-61",
                            "recommended_next": "planner_merge",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_dev_secondary:gpt-5.4",
                ),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-07B",
                task_kind="delivery",
                message="Rate limit fallback path",
                ttl_min=15,
                backend="codex_exec",
                timeout_seconds=30,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")
        self.assertEqual(payload["model"], "gpt-5.4")

    def test_run_openclaw_rate_limit_path_is_never_entered(self) -> None:
        with (
            patch.dict(os.environ, {"FC_ALLOW_OPENCLAW_SUBAGENT_PROVIDER": "1"}, clear=False),
            patch.object(
                MODULE,
                "_run_codex_exec_subagent",
                return_value=(
                    0,
                    json.dumps({"status": "completed", "summary": "codex fallback due to deprecated openclaw provider", "artifact": "artifact.txt", "verify": "proof=codex_exec", "files_touched": "src/app.py", "tests_run": "pytest -q", "commit_sha": "abc1234", "architecture_check": "layer=api", "vision_alignment": "batch=BATCH-61", "recommended_next": "planner_merge", "blocking_issue": "none"}),
                    "",
                    "codex_exec:planner_dev_openclaw:gpt-5.4",
                ),
            ) as codex_mock,
            patch.object(
                MODULE.subprocess,
                "run",
                return_value=type(
                    "CompletedProcess",
                    (),
                    {"returncode": 1, "stdout": "", "stderr": "api-rate-limit-reached http 429 quota exhausted"},
                )(),
            ),
            patch.object(
                MODULE,
                "model_plane_run_secondary_then_qwen_fallback",
                return_value=(0, json.dumps({"status": "completed", "summary": "qwen rescue", "artifact": "artifact.txt", "verify": "proof=qwen", "files_touched": "src/app.py", "tests_run": "pytest -q", "commit_sha": "abc1234", "architecture_check": "layer=api", "vision_alignment": "batch=BATCH-61", "recommended_next": "planner_merge", "blocking_issue": "none"}), "", "qwen:planner_dev_openclaw"),
            ),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-08",
                task_kind="delivery",
                message="OpenClaw quota fallback path",
                ttl_min=15,
                backend="openclaw",
                timeout_seconds=120,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")
        codex_mock.assert_called_once()

    def test_run_openclaw_cached_codex_rate_limit_path_is_never_entered(self) -> None:
        with (
            patch.dict(os.environ, {"FC_ALLOW_OPENCLAW_SUBAGENT_PROVIDER": "1"}, clear=False),
            patch.object(
                MODULE,
                "_run_codex_exec_subagent",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "codex exec handled deprecated openclaw backend",
                            "artifact": "artifact.txt",
                            "verify": "proof=codex_exec",
                            "files_touched": "platform/automation/planner_subagent_manager.py",
                            "tests_run": "python3 -m unittest platform.automation.tests.test_planner_subagent_manager",
                            "commit_sha": "abc1234",
                            "architecture_check": "layer=platform",
                            "vision_alignment": "batch=BATCH-61",
                            "recommended_next": "planner_merge",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_dev_openclaw:gpt-5.4",
                ),
            ) as codex_mock,
            patch.object(
                MODULE,
                "model_plane_run_secondary_then_qwen_fallback",
                return_value=(
                    0,
                    json.dumps(
                        {
                            "status": "completed",
                            "summary": "secondary codex rescued openclaw cache path",
                            "artifact": "artifact.txt",
                            "verify": "proof=secondary-openclaw-cache",
                            "files_touched": "platform/automation/planner_subagent_manager.py",
                            "tests_run": "python3 -m unittest platform.automation.tests.test_planner_subagent_manager",
                            "commit_sha": "abc1234",
                            "architecture_check": "layer=platform",
                            "vision_alignment": "batch=BATCH-61",
                            "recommended_next": "planner_merge",
                            "blocking_issue": "none",
                        }
                    ),
                    "",
                    "codex_exec:planner_dev_openclaw:gpt-5.4",
                ),
            ) as fallback_mock,
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="dev",
                owner_task_id="BATCH-61-DEV-08B",
                task_kind="delivery",
                message="OpenClaw cached codex rate limit fallback path",
                ttl_min=15,
                backend="openclaw",
                timeout_seconds=120,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "codex_exec")
        self.assertEqual(payload["backend_route_reason"], "secondary_codex_fallback")
        fallback_mock.assert_not_called()
        codex_mock.assert_called_once()

    def test_qwen_fallback_ignores_interactive_oauth_prompt(self) -> None:
        with (
            patch.object(
                sys.modules["runtime.model_plane.model_plane"],
                "planner_qwen_fallback_enabled",
                return_value=True,
            ),
            patch.object(
                sys.modules["runtime.model_plane.model_plane"],
                "active_rate_limit_reason",
                return_value="",
            ),
            patch.object(
                sys.modules["runtime.model_plane.model_plane"],
                "run_qwen_cli",
                return_value=(
                    0,
                    "Qwen OAuth Authentication\nPlease visit this URL to authorize\nWaiting for authorization.\n",
                    "",
                    "qwen:planner_dev_oauth",
                ),
            ),
        ):
            result = MODULE.model_plane_run_qwen_cli_fallback(
                prompt="Reply with OK only.",
                timeout_seconds=30,
                subagent_id="planner_dev_oauth",
                reason="forced_codex_quota_test",
                source="cache",
                env={"FC_PLANNER_QWEN_FALLBACK": "1"},
            )

        self.assertIsNone(result)

    def test_qwen_fallback_ignores_missing_auth_type_probe_output(self) -> None:
        with (
            patch.object(
                sys.modules["runtime.model_plane.model_plane"],
                "planner_qwen_fallback_enabled",
                return_value=True,
            ),
            patch.object(
                sys.modules["runtime.model_plane.model_plane"],
                "active_rate_limit_reason",
                return_value="",
            ),
            patch.object(
                sys.modules["runtime.model_plane.model_plane"],
                "run_qwen_cli",
                return_value=(
                    1,
                    "",
                    "No auth type is selected. Please configure an auth type before running in non-interactive mode.",
                    "qwen:planner_dev_noauth",
                ),
            ),
        ):
            result = MODULE.model_plane_run_qwen_cli_fallback(
                prompt="Reply with OK only.",
                timeout_seconds=30,
                subagent_id="planner_dev_noauth",
                reason="forced_codex_quota_test",
                source="cache",
                env={"FC_PLANNER_QWEN_FALLBACK": "1"},
            )

        self.assertIsNone(result)

    def test_run_codex_exec_full_access_uses_bypass_flag_instead_of_invalid_sandbox_value(self) -> None:
        captured: dict[str, object] = {}

        def _fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            out_path = Path(cmd[cmd.index("-o") + 1])
            out_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "summary": "ok",
                        "artifact": "artifact.txt",
                        "verify": "proof=codex_exec",
                        "files_touched": "none",
                        "tests_run": "SKIP(no_tests)",
                        "commit_sha": "none",
                        "architecture_check": "layer=runtime",
                        "vision_alignment": "batch=BATCH-61",
                        "recommended_next": "planner_merge",
                        "blocking_issue": "none",
                    }
                ),
                encoding="utf-8",
            )
            return type("CompletedProcess", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        with (
            patch.object(MODULE, "_openclaw_agent_ids", return_value=set()),
            patch.object(MODULE.subprocess, "run", side_effect=_fake_run),
        ):
            rc, payload = run_subagent(
                self.config,
                role="planner",
                target_role="admin",
                owner_task_id="BATCH-61-ADMIN-10",
                task_kind="runtime",
                message="Repair runtime truth.",
                ttl_min=15,
                backend="codex_exec",
                timeout_seconds=30,
            )

        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        cmd = captured["cmd"]
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertNotIn("--sandbox", cmd)

    def test_shared_root_is_canonicalized_to_vm_workspace(self) -> None:
        canonical = Path("/home/venom/analyse-financiere")
        shared = Path("/home/venom/shared/analyse-financiere")
        if not canonical.exists() or not shared.exists():
            self.skipTest("canonical/shared VM workspaces unavailable")
        self.assertEqual(_canonical_runtime_root(shared.resolve()), canonical)

    def test_runtime_relpath_handles_shared_vm_alias(self) -> None:
        canonical = Path("/home/venom/analyse-financiere")
        shared = Path("/home/venom/shared/analyse-financiere")
        if not canonical.exists() or not shared.exists():
            self.skipTest("canonical/shared VM workspaces unavailable")
        target = shared / "logs-codex-runs" / "orchestrator-state" / "legacy" / "planner-subagents-results" / "example.raw.txt"
        self.assertEqual(
            _runtime_relpath(target, canonical),
            "logs-codex-runs/orchestrator-state/legacy/planner-subagents-results/example.raw.txt",
        )


if __name__ == "__main__":
    unittest.main()
