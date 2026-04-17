from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from runtime.core.contracts import PlannerGraphState
from runtime.truth.event_store import EventStore


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "runtime" / "truth" / "runtime_truth_reader.py"
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot, load_product_delivery_state, product_delivery_state_path


class RuntimeTruthReaderTests(unittest.TestCase):
    def test_api_wave_state_exposes_next_endpoint_when_runtime_is_idle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
            manifest_dir = root / "platform" / "automation" / "config"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "api_wave_manifest.v1.json").write_text(
                json.dumps(
                    {
                        "schema_version": "api_wave_manifest.v1",
                        "mode": "api_autonomy",
                        "enabled": True,
                        "stream_id": "API-WAVE",
                        "endpoints": [
                            {
                                "endpoint_id": "copilot_search",
                                "domain": "copilot",
                                "route_path": "/api/copilot/search",
                                "route_module": "apps/api/src/domains/copilot/api/search.py",
                                "priority": "P1",
                                "product_surface": "copilot",
                                "shared_contract": "copilot_search_v1",
                                "endpoint_service": "copilot_search_endpoint_service.py",
                                "parity_status": "route_heavy",
                                "last_public_proof": "none",
                                "deferred_reason": "none",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=8, event_limit=8, ec2_reachable=True)
            delivery_state = snapshot["product_delivery_state"]
            api_wave = snapshot["api_wave_state"]

            self.assertTrue(delivery_state["api_autonomy_mode"])
            self.assertTrue(api_wave["enabled"])
            self.assertTrue(api_wave["dispatch_ready"])
            self.assertEqual(api_wave["current_endpoint"]["endpoint_id"], "copilot_search")
            self.assertEqual(api_wave["current_task_id"], "APIWAVE-COPILOT_SEARCH-DEV-01")

    def test_product_done_clears_active_batch_monotonically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-91"],
                            "novelty_target": "portfolio_first_brief_with_ranked_actions",
                            "user_visible_delta": "daily brief surfaces the top action",
                        },
                        "items": [
                            {
                                "id": "BATCH-91",
                                "state": "IN_PROGRESS",
                                "user_value_delta_visible": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-91"]},
                        "tasks": [{"id": "BATCH-91-DEV-01", "stream_id": "BATCH-91", "role": "dev", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-91",
                    task_id="BATCH-91-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-04-17T00:35:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-91-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "public ec2 healthy for batch close",
                        "artifact": "GET http://3.98.20.77/api/health => ok",
                        "proof_manifest": "proof-manifest://batch-91-close",
                        "verify": "monitor reports health=OK on public EC2",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)
            delivery_state = snapshot["product_delivery_state"]

            self.assertIsNone(delivery_state["active_batch_id"])
            self.assertTrue(delivery_state["product_done"])
            self.assertEqual(delivery_state["phase"], "product_done_ops_dirty")
            self.assertEqual(delivery_state["last_completed_batch_id"], "BATCH-91")
            self.assertEqual(delivery_state["close_reason"], "public_proof_ok")

    def test_active_batch_without_contract_stays_active_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-92"],
                            "novelty_target": "portfolio_first_brief_with_ranked_actions",
                            "user_visible_delta": "daily brief surfaces the top action",
                        },
                        "items": [
                            {
                                "id": "BATCH-92",
                                "state": "IN_PROGRESS",
                                "novelty_target": "portfolio_first_brief_with_ranked_actions",
                                "user_visible_delta": "daily brief surfaces the top action",
                                "user_value_delta_visible": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-92"]},
                        "tasks": [{"id": "BATCH-92-DEV-01", "stream_id": "BATCH-92", "role": "dev", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-92",
                    task_id="BATCH-92-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-04-17T00:40:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-92-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "implementation finished awaiting public proof",
                        "artifact": "proof://batch-92",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)
            delivery_state = snapshot["product_delivery_state"]

            self.assertEqual(delivery_state["active_batch_id"], "BATCH-92")
            self.assertEqual(delivery_state["phase"], "active_delivery")
            self.assertEqual(delivery_state["freeze_reason"], "missing_batch_contract")

    def test_active_batch_with_complete_contract_enters_verifying_public_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-93"],
                            "novelty_target": "portfolio_first_brief_with_ranked_actions",
                            "user_visible_delta": "daily brief surfaces the top action",
                            "api_proof": {"url": "http://3.98.20.77/api/copilot/start", "expect": "200"},
                            "ui_proof": {"url": "http://3.98.20.77/", "expect": "top portfolio action"},
                            "done_when": "public api and ui smoke green",
                        },
                        "items": [
                            {
                                "id": "BATCH-93",
                                "state": "IN_PROGRESS",
                                "novelty_target": "portfolio_first_brief_with_ranked_actions",
                                "user_visible_delta": "daily brief surfaces the top action",
                                "user_value_delta_visible": 1,
                                "api_proof": {"url": "http://3.98.20.77/api/copilot/start", "expect": "200"},
                                "ui_proof": {"url": "http://3.98.20.77/", "expect": "top portfolio action"},
                                "done_when": "public api and ui smoke green",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-93"]},
                        "tasks": [{"id": "BATCH-93-DEV-01", "stream_id": "BATCH-93", "role": "dev", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-93",
                    task_id="BATCH-93-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-04-17T00:45:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-93-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "implementation finished awaiting public proof",
                        "artifact": "proof://batch-93",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)
            delivery_state = snapshot["product_delivery_state"]

            self.assertEqual(delivery_state["active_batch_id"], "BATCH-93")
            self.assertEqual(delivery_state["phase"], "verifying_public_proof")
            self.assertEqual(delivery_state["freeze_reason"], "waiting_public_proof")

    def test_persist_delivery_state_writes_canonical_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-91"],
                            "recent_completed_batch_ids": ["BATCH-90"],
                            "novelty_target": "portfolio_first_brief_with_ranked_actions",
                            "user_visible_delta": "daily brief surfaces the top action",
                        },
                        "items": [{"id": "BATCH-91", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-91"]},
                        "tasks": [{"id": "BATCH-91-DEV-01", "stream_id": "BATCH-91", "role": "dev", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-91",
                    task_id="BATCH-91-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-04-17T00:35:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-91-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "public api healthy on http://3.98.20.77 for batch verification",
                        "artifact": "proof://batch-91",
                        "proof_manifest": "proof-manifest://batch-91",
                        "verify": "curl http://3.98.20.77/api/health",
                        "tests_run": "smoke_ec2_public",
                        "commit_sha": "abc12345",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(
                root,
                state_limit=12,
                event_limit=24,
                ec2_reachable=True,
                persist_delivery_state=True,
            )

            state_path = product_delivery_state_path(root)
            self.assertEqual(snapshot["product_delivery_state_path"], str(state_path))
            self.assertTrue(state_path.exists())
            persisted = load_product_delivery_state(root)
            self.assertEqual(persisted["phase"], "product_done_ops_dirty")
            self.assertEqual(persisted["last_completed_batch_id"], "BATCH-91")
            self.assertEqual(persisted["last_completion_proof_ref"], "proof-manifest://batch-91")
            self.assertEqual(persisted["close_reason"], "public_proof_ok")
            self.assertEqual(persisted["schema_version"], "product_delivery_state.v1")

    def test_event_store_primary_ignores_historical_states_when_no_open_cycle_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [{"id": "BATCH-89", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-89-DEV-03", "stream_id": "BATCH-89", "role": "dev", "state": "DONE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-89",
                    task_id="BATCH-89-DEV-03",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-04-15T16:43:55Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-89-DEV-03", "target_role": "dev"},
                    capability_result={"status": "pass", "backend": "codex_exec", "summary": "historical merge residue"},
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)

            self.assertTrue(snapshot["event_store_primary"])
            self.assertEqual(snapshot["graph_state_count_total"], 1)
            self.assertEqual(snapshot["ignored_historical_state_count"], 1)
            self.assertEqual(snapshot["graph_state_count"], 0)
            self.assertEqual(snapshot["latest_states"], [])

    def test_event_store_primary_filters_latest_states_to_active_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-86"]},
                        "items": [{"id": "BATCH-86", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-86"]},
                        "tasks": [
                            {"id": "BATCH-86-ARCH", "stream_id": "BATCH-86", "role": "planner", "state": "IN_PROGRESS"},
                            {"id": "BATCH-84-ADMIN-01", "stream_id": "BATCH-84", "role": "admin", "state": "DONE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-84",
                    task_id="BATCH-84-ADMIN-01",
                    task_kind="governance",
                    owner_role="planner",
                    target_role="admin",
                    status="retryable",
                    current_node="close_or_requeue",
                    updated_at="2026-04-15T08:10:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-84-ADMIN-01", "target_role": "admin"},
                    capability_result={
                        "status": "failed",
                        "backend": "codex_exec",
                        "summary": "invalid_subagent_result:start_banner_only",
                        "blocking_issue": "invalid_subagent_result:start_banner_only",
                    },
                )
            )
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-86",
                    task_id="BATCH-86-ARCH",
                    task_kind="architecture",
                    owner_role="planner",
                    target_role="planner",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-04-15T08:20:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-86-ARCH", "target_role": "planner"},
                    capability_result={"status": "running", "backend": "codex_exec", "summary": "architecture audit in progress"},
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=False)

            self.assertTrue(snapshot["event_store_primary"])
            self.assertFalse(snapshot["projection_secondary_only"])
            self.assertEqual(snapshot["graph_state_count_total"], 2)
            self.assertEqual(snapshot["ignored_historical_state_count"], 0)
            self.assertEqual([row["task_id"] for row in snapshot["latest_states"]], ["BATCH-86-ARCH"])
            self.assertEqual([row["batch_id"] for row in snapshot["latest_states"]], ["BATCH-86"])
            self.assertEqual(snapshot["quarantined_retryable_residue_count"], 1)
            delivery_state = snapshot["product_delivery_state"]
            self.assertEqual(delivery_state["phase"], "external_outage")
            self.assertEqual(delivery_state["active_batch_id"], "BATCH-86")
            self.assertFalse(delivery_state["next_batch_eligible"])

    def test_done_owner_task_quarantines_retryable_residue_without_invalid_result_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-87"]},
                        "items": [{"id": "BATCH-87", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-87"]},
                        "tasks": [
                            {"id": "BATCH-87-ADMIN-01", "stream_id": "BATCH-87", "role": "admin", "state": "DONE"},
                            {"id": "BATCH-87-GOV_REVIEW", "stream_id": "BATCH-87", "role": "planner", "state": "IN_PROGRESS"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-87",
                    task_id="BATCH-87-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="retryable",
                    current_node="close_or_requeue",
                    updated_at="2026-04-15T11:18:36Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-87-ADMIN-01", "target_role": "admin"},
                    capability_result={
                        "status": "failed",
                        "backend": "codex_exec",
                        "summary": "Cannot continue with precise SQLite-based runtime audit yet because query command failed; retrying with corrected quoting.",
                        "blocking_issue": "SQL quoting error.",
                        "artifact": "None.",
                        "verify": "None.",
                        "tests_run": "None.",
                        "commit_sha": "none",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)

            self.assertEqual(snapshot["graph_state_count"], 0)
            self.assertEqual(snapshot["quarantined_retryable_residue_count"], 1)
            quarantined = snapshot["quarantined_retryable_residue"][0]
            self.assertEqual(quarantined["task_id"], "BATCH-87-ADMIN-01")
            self.assertEqual(quarantined["status"], "quarantined")
            self.assertEqual(quarantined["blocking_issue"], "quarantined_retryable_residue:done")

    def test_maintenance_window_does_not_become_external_outage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-96"]},
                        "items": [{"id": "BATCH-96", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-96"]},
                        "tasks": [
                            {"id": "BATCH-96-DEV-02", "stream_id": "BATCH-96", "role": "dev", "state": "IN_PROGRESS"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-96",
                    task_id="BATCH-96-DEV-02",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-04-17T00:07:46Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-96-DEV-02", "target_role": "dev"},
                    capability_result={"status": "running", "backend": "codex_exec", "summary": "public restart window"},
                )
            )

            snapshot = build_runtime_truth_snapshot(
                root,
                state_limit=12,
                event_limit=24,
                ec2_reachable=False,
                public_probe_status="error",
                maintenance_active=True,
                maintenance_details={
                    "maintenance_active": True,
                    "maintenance_reason": "runtime_restart_in_progress",
                    "maintenance_command": "restart",
                    "maintenance_age_s": 14,
                    "maintenance_source": "remote_runtime_lock_meta",
                },
            )

            delivery_state = snapshot["product_delivery_state"]
            self.assertEqual(delivery_state["phase"], "active_delivery")
            self.assertEqual(delivery_state["freeze_reason"], "none")
            self.assertTrue(delivery_state["maintenance_active"])
            self.assertTrue(delivery_state["ec2_reachable"])
            self.assertEqual(delivery_state["maintenance_reason"], "runtime_restart_in_progress")

    def test_done_owner_task_quarantines_historical_ready_to_merge_residue_with_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [{"id": "BATCH-90", "state": "CLOSED"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {"id": "BATCH-90-ADMIN-01", "stream_id": "BATCH-90", "role": "admin", "state": "DONE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-90",
                    task_id="BATCH-90-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="ready_to_merge",
                    current_node="apply_workboard_mutation",
                    updated_at="2026-04-15T19:08:09Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-90-ADMIN-01", "target_role": "admin"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "Runtime unblock verified. public api healthy.",
                        "artifact": "commit=d87d334f",
                        "verify": "pytest -q target && curl http://3.98.20.77/api/health",
                        "tests_run": "pytest -q target",
                        "commit_sha": "d87d334f",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)

            self.assertTrue(snapshot["event_store_primary"])
            self.assertEqual(snapshot["graph_state_count"], 0)
            self.assertEqual(snapshot["ignored_historical_state_count"], 0)
            self.assertEqual(snapshot["quarantined_retryable_residue_count"], 1)
            quarantined = snapshot["quarantined_retryable_residue"][0]
            self.assertEqual(quarantined["task_id"], "BATCH-90-ADMIN-01")
            self.assertEqual(quarantined["status"], "quarantined")
            self.assertEqual(quarantined["blocking_issue"], "quarantined_retryable_residue:done")
            delivery_state = snapshot["product_delivery_state"]
            self.assertEqual(delivery_state["phase"], "idle_ready_for_next_batch")
            self.assertTrue(delivery_state["product_done"])
            self.assertTrue(delivery_state["next_batch_eligible"])
            self.assertIsNone(delivery_state["active_batch_id"])

    def test_public_proof_makes_product_done_monotone_before_ops_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-91"]},
                        "items": [{"id": "BATCH-91", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-91"]},
                        "tasks": [
                            {"id": "BATCH-91-DEV-01", "stream_id": "BATCH-91", "role": "dev", "state": "IN_PROGRESS"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-91",
                    task_id="BATCH-91-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="close_or_requeue",
                    updated_at="2026-04-16T23:35:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-91-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "public api healthy on http://3.98.20.77 for batch verification",
                        "artifact": "proof://batch-91",
                        "verify": "curl http://3.98.20.77/api/health",
                        "tests_run": "smoke_ec2_public",
                        "commit_sha": "abc12345",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)

            delivery_state = snapshot["product_delivery_state"]
            self.assertIsNone(delivery_state["active_batch_id"])
            self.assertEqual(delivery_state["phase"], "product_done_ops_dirty")
            self.assertTrue(delivery_state["product_done"])
            self.assertFalse(delivery_state["ops_clean"])
            self.assertTrue(delivery_state["next_batch_eligible"])
            self.assertEqual(delivery_state["last_completed_batch_id"], "BATCH-91")

    def test_historical_public_proof_does_not_close_newer_active_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-101"],
                            "recent_completed_batch_ids": ["BATCH-100"],
                        },
                        "items": [{"id": "BATCH-101", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-101"]},
                        "tasks": [
                            {"id": "BATCH-101-DEV-01", "stream_id": "BATCH-101", "role": "dev", "state": "IN_PROGRESS"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-100",
                    task_id="BATCH-100-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="merged",
                    current_node="close_or_requeue",
                    updated_at="2026-04-15T09:00:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-100-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "completed",
                        "backend": "codex_exec",
                        "summary": "public api healthy on http://3.98.20.77",
                        "artifact": "proof://batch-100",
                        "proof_manifest": "proof-manifest://batch-100",
                        "verify": "curl http://3.98.20.77/api/health",
                        "tests_run": "smoke_ec2_public",
                    },
                )
            )
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-101",
                    task_id="BATCH-101-DEV-01",
                    task_kind="delivery",
                    owner_role="planner",
                    target_role="dev",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-04-15T09:05:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-101-DEV-01", "target_role": "dev"},
                    capability_result={
                        "status": "running",
                        "backend": "codex_exec",
                        "summary": "implementing current batch delta",
                    },
                )
            )

            snapshot = build_runtime_truth_snapshot(
                root,
                state_limit=12,
                event_limit=24,
                ec2_reachable=True,
            )

            delivery_state = snapshot["product_delivery_state"]
            self.assertEqual(delivery_state["active_batch_id"], "BATCH-101")
            self.assertFalse(delivery_state["product_done"])
            self.assertEqual(delivery_state["phase"], "active_delivery")
            self.assertEqual(delivery_state["current_public_proof"]["status"], "none")
            self.assertEqual(delivery_state["last_completed_batch_id"], "BATCH-100")
            self.assertEqual(delivery_state["close_reason"], "public_proof_ok")

    def test_merged_active_cycle_residue_becomes_idle_ready_for_next_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-96"],
                            "novelty_target": "portfolio_first_brief_with_ranked_actions",
                            "user_visible_delta": "daily brief surfaces the top portfolio or watchlist action and opens an investment memo in one click",
                        },
                        "items": [{"id": "BATCH-96", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-96"]},
                        "tasks": [
                            {"id": "BATCH-96-DEV-01", "stream_id": "BATCH-96", "role": "dev", "state": "DONE"},
                            {"id": "BATCH-96-DEV-02", "stream_id": "BATCH-96", "role": "dev", "state": "DONE"},
                            {"id": "BATCH-96-DEV-03", "stream_id": "BATCH-96", "role": "dev", "state": "DONE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            for task_id, updated_at in (
                ("BATCH-96-DEV-01", "2026-04-16T23:50:23Z"),
                ("BATCH-96-DEV-02", "2026-04-17T00:14:57Z"),
                ("BATCH-96-DEV-03", "2026-04-17T00:29:06Z"),
            ):
                store.upsert_graph_state(
                    PlannerGraphState(
                        batch_id="BATCH-96",
                        task_id=task_id,
                        task_kind="delivery",
                        owner_role="planner",
                        target_role="dev",
                        status="merged",
                        current_node="close_or_requeue",
                        updated_at=updated_at,
                        engine="langgraph",
                        capability_request={"backend": "codex_exec", "task_id": task_id, "target_role": "dev"},
                        capability_result={
                            "status": "completed",
                            "backend": "codex_exec",
                            "summary": "public api healthy on http://3.98.20.77",
                            "artifact": f"proof://{task_id.lower()}",
                            "verify": "curl http://3.98.20.77/api/health",
                            "tests_run": "smoke_ec2_public",
                            "commit_sha": "abc12345",
                        },
                    )
                )

            snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24, ec2_reachable=True)

            delivery_state = snapshot["product_delivery_state"]
            self.assertIsNone(delivery_state["active_batch_id"])
            self.assertEqual(delivery_state["phase"], "idle_ready_for_next_batch")
            self.assertTrue(delivery_state["product_done"])
            self.assertFalse(delivery_state["ops_clean"])
            self.assertTrue(delivery_state["next_batch_eligible"])
            self.assertEqual(delivery_state["last_completed_batch_id"], "BATCH-96")
            self.assertEqual(delivery_state["close_reason"], "public_proof_ok")
            self.assertIsNotNone(delivery_state["last_closed_at"])
            self.assertIsNotNone(delivery_state["last_completion_proof_ref"])
            self.assertIn("active_cycle_projection_without_canonical_active_batch", delivery_state["advisory_mismatch"])
            self.assertEqual(
                delivery_state["current_value_target"]["novelty_target"],
                "portfolio_first_brief_with_ranked_actions",
            )

    def test_persist_delivery_state_writes_canonical_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")

            snapshot = build_runtime_truth_snapshot(
                root,
                state_limit=12,
                event_limit=24,
                ec2_reachable=True,
                public_probe_status="ok",
                persist_delivery_state=True,
            )

            state_path = Path(snapshot["product_delivery_state_path"])
            self.assertTrue(state_path.exists())
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["phase"], snapshot["product_delivery_state"]["phase"])
            self.assertEqual(persisted["active_batch_id"], snapshot["product_delivery_state"]["active_batch_id"])
            self.assertEqual(persisted["close_reason"], snapshot["product_delivery_state"]["close_reason"])


if __name__ == "__main__":
    unittest.main()
