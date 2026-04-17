from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from runtime.core.contracts import PlannerGraphState
from runtime.truth.event_store import EventStore


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

if "yaml" not in sys.modules:
    fake_yaml = types.ModuleType("yaml")
    fake_yaml.safe_load = lambda *args, **kwargs: {}
    fake_yaml.safe_dump = lambda *args, **kwargs: ""
    sys.modules["yaml"] = fake_yaml

MODULE_PATH = AUTOMATION_DIR / "runtime" / "planner" / "planner_runtime_actions.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_runtime_actions", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_runtime_actions"] = MODULE
SPEC.loader.exec_module(MODULE)


class PlannerRuntimeActionsCollectTests(unittest.TestCase):
    def test_default_browser_urls_follow_public_ec2_runtime(self) -> None:
        self.assertEqual(MODULE.DEFAULT_BROWSER_FRONTEND_URL, "http://3.98.20.77")
        self.assertEqual(MODULE.DEFAULT_BROWSER_MONITOR_URL, "http://3.98.20.77:8080")

    def test_parse_iso_utc_accepts_fractional_zulu_timestamp(self) -> None:
        parsed = MODULE._parse_iso_utc("2026-04-16T05:03:05.737683Z")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.isoformat(), "2026-04-16T05:03:05.737683+00:00")

    def test_complete_status_is_treated_as_success(self) -> None:
        self.assertIn("complete", MODULE.SUCCESS_SUBAGENT_STATUSES)

    def test_failed_status_with_delivery_proof_is_treated_as_semantic_success(self) -> None:
        payload = {
            "status": "failed",
            "artifact": "docs/proof.md",
            "verify": "before=x; after=y; test=z",
            "tests_run": "pytest -q test_example.py",
            "commit_sha": "abc123",
            "blocking_issue": "none",
        }

        self.assertTrue(MODULE._payload_semantic_success(payload, target_role="dev"))

    def test_failed_status_with_delivery_proof_and_blocking_issue_is_not_semantic_success(self) -> None:
        payload = {
            "status": "failed",
            "artifact": "docs/proof.md",
            "verify": "before=x; after=y; test=z",
            "tests_run": "pytest -q test_example.py",
            "commit_sha": "abc123",
            "blocking_issue": "subagent_failed",
        }

        self.assertFalse(MODULE._payload_semantic_success(payload, target_role="dev"))

    def test_placeholder_only_delivery_fields_do_not_count_as_evidence(self) -> None:
        payload = {
            "status": "failed",
            "artifact": "...",
            "verify": "before=...; after=...; test=...",
            "tests_run": "...",
            "commit_sha": "...",
            "blocking_issue": "none",
        }

        self.assertFalse(MODULE._payload_has_delivery_evidence(payload, target_role="dev"))
        self.assertFalse(MODULE._payload_semantic_success(payload, target_role="dev"))

    def test_planner_autofill_treats_placeholder_values_as_missing(self) -> None:
        self.assertTrue(MODULE._planner_evidence_needs_autofill("..."))
        self.assertTrue(MODULE._planner_evidence_needs_autofill("before=...; after=...; test=..."))
        self.assertFalse(MODULE._planner_evidence_needs_autofill("before=500; after=200; test=pytest"))

    def test_auto_architecture_checks_returns_contract_format(self) -> None:
        payload = MODULE._auto_architecture_checks(
            {
                "id": "BATCH-95-ARCH",
                "artifact": "docs/architecture/ARCHITECTURE_MAP.md",
            }
        )

        self.assertIn("layer=platform", payload)
        self.assertIn("imports_ok=yes", payload)
        self.assertIn("path_target=docs/architecture/ARCHITECTURE_MAP.md", payload)

    def test_collect_finished_admin_subagents_skips_done_owner_without_collecting(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            legacy = orch / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-84"]},
                        "tasks": [
                            {
                                "id": "BATCH-84-ADMIN-01",
                                "stream_id": "BATCH-84",
                                "role": "admin",
                                "state": "DONE",
                                "completed_at": "2026-04-15T00:00:00Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (legacy / "planner-subagents-registry.json").write_text(
                json.dumps(
                    {
                        "subagents": [
                            {
                                "subagent_id": "planner_admin_done",
                                "parent_role": "planner",
                                "target_role": "admin",
                                "owner_task_id": "BATCH-84-ADMIN-01",
                                "status": "running",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            results_dir = legacy / "planner-subagents-results"
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "planner_admin_done.raw.txt").write_text("stale compat payload", encoding="utf-8")

            with mock.patch.object(MODULE, "collect_subagent", side_effect=AssertionError("collect_subagent should not run")):
                actions = MODULE._collect_finished_admin_subagents(root, source="unit_test")

            self.assertIn("admin_skip_done:BATCH-84-ADMIN-01", actions)
            registry = json.loads((legacy / "planner-subagents-registry.json").read_text(encoding="utf-8"))
            self.assertEqual(registry.get("subagents"), [])

    def test_mark_stale_dev_subagents_terminates_failed_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            legacy = orch / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": ["BATCH-85"]}, "items": []}),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-85"]},
                        "tasks": [
                            {
                                "id": "BATCH-85-DEV-03",
                                "stream_id": "BATCH-85",
                                "role": "dev",
                                "state": "IN_PROGRESS",
                                "status": "IN_PROGRESS",
                                "updated_at": "2026-03-06T12:00:00Z",
                                "last_progress_at": "2026-03-06T12:00:00Z",
                                "dev_no_progress_streak": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (legacy / "planner-subagents-registry.json").write_text(
                json.dumps(
                    {
                        "subagents": [
                            {
                                "subagent_id": "planner_dev_stale",
                                "parent_role": "planner",
                                "target_role": "dev",
                                "owner_task_id": "BATCH-85-DEV-03",
                                "status": "running",
                                "backend": "codex_exec",
                                "created_at": "2026-03-06T12:00:00Z",
                                "last_update_at": "2026-03-06T12:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            results_dir = legacy / "planner-subagents-results"
            results_dir.mkdir(parents=True, exist_ok=True)

            with mock.patch.object(MODULE, "_terminate_planner_subagent_launcher", return_value=True) as terminate:
                actions = MODULE._mark_stale_dev_subagents(root, source="unit_test")

            self.assertIn("dev_recovery_required:BATCH-85-DEV-03", actions)
            terminate.assert_called_once_with("planner_dev_stale")
            registry = json.loads((legacy / "planner-subagents-registry.json").read_text(encoding="utf-8"))
            row = registry["subagents"][0]
            self.assertEqual(row["status"], "failed")
            self.assertEqual(row["blocking_issue"], "stalled_delivery")

    def test_has_active_subagent_keeps_running_row_active_even_when_raw_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            legacy = orch / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": ["BATCH-87"]}, "items": []}),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-87"]},
                        "tasks": [
                            {
                                "id": "BATCH-87-DEV-03",
                                "stream_id": "BATCH-87",
                                "role": "dev",
                                "state": "IN_PROGRESS",
                                "status": "IN_PROGRESS",
                                "updated_at": "2026-04-15T10:52:02Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (legacy / "planner-subagents-registry.json").write_text(
                json.dumps(
                    {
                        "subagents": [
                            {
                                "subagent_id": "planner_dev_live",
                                "parent_role": "planner",
                                "target_role": "dev",
                                "owner_task_id": "BATCH-87-DEV-03",
                                "status": "running",
                                "backend": "codex_exec",
                                "created_at": "2026-04-15T10:52:02Z",
                                "last_update_at": "2026-04-15T10:52:02Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            results_dir = legacy / "planner-subagents-results"
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "planner_dev_live.raw.txt").write_text(
                "OpenAI Codex v0.114.0\nstill running\n",
                encoding="utf-8",
            )

            self.assertTrue(MODULE._has_active_subagent(root, "dev"))


class PlannerRuntimeActionsAdminGuardTests(unittest.TestCase):
    def test_record_admin_failure_uses_combined_recoverable_streaks_for_takeover(self) -> None:
        board = {
            "tasks": [
                {
                    "id": "BATCH-85-ADMIN-01",
                    "stream_id": "BATCH-85",
                    "role": "admin",
                    "state": "IN_PROGRESS",
                    "admin_timeout_streak": 2,
                    "admin_invalid_result_streak": 0,
                    "planner_takeover_required": False,
                }
            ],
            "events": [],
        }

        result = MODULE._record_admin_failure(
            board,
            task_id_value="BATCH-85-ADMIN-01",
            source="unit_test",
            subagent_id="planner_admin_loop",
            blocking_issue="invalid_subagent_result:start_banner_only",
            event_kind="planner_orchestrator_admin_dispatch_failed",
        )

        task = board["tasks"][0]
        self.assertEqual(result, "planner_takeover_required")
        self.assertTrue(task["planner_takeover_required"])
        self.assertEqual(task["admin_timeout_streak"], 2)
        self.assertEqual(task["admin_invalid_result_streak"], 1)
        self.assertEqual(task["planner_takeover_reason"], "admin_invalid_result_streak:1")
        takeover_events = [event for event in board["events"] if event.get("kind") == "planner_orchestrator_admin_takeover_required"]
        self.assertEqual(len(takeover_events), 1)
        self.assertEqual(takeover_events[0]["details"].get("combined_streak"), 3)

    def test_dispatch_admin_capability_escalates_existing_mixed_streak_task_to_takeover(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": ["BATCH-85"]}, "items": []}),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-85"]},
                        "tasks": [
                            {
                                "id": "BATCH-85-ADMIN-01",
                                "stream_id": "BATCH-85",
                                "role": "admin",
                                "state": "READY_PLANNER",
                                "admin_timeout_streak": 2,
                                "admin_invalid_result_streak": 1,
                                "planner_takeover_required": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(MODULE, "_planner_takeover_admin_task", return_value={"dispatched": True, "backend": "planner_takeover"}) as takeover:
                result = MODULE._dispatch_admin_capability(root, source="unit_test", backend="codex_exec")

        self.assertEqual(result["backend"], "planner_takeover")
        takeover.assert_called_once()


class PlannerRuntimeActionsAutobatchGuardTests(unittest.TestCase):
    def test_planner_autobatch_ignores_stale_waiting_sqlite_residue_without_active_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(json.dumps({"items": [], "meta": {}}), encoding="utf-8")
            board_path.write_text(
                json.dumps(
                    {
                        "streams": [],
                        "tasks": [],
                        "events": [],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-88",
                    task_id="BATCH-88-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2026-04-15T15:18:51Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-88-ADMIN-01", "target_role": "admin"},
                    capability_result={"status": "running", "backend": "codex_exec", "summary": "orphan historical residue"},
                )
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(reason="planner_always_active", cooldown_s=0, source="unit_test")
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_OK", out)
            self.assertIn("batch_id=BATCH-01", out)
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in queue.get("items", [])], ["BATCH-01"])
            board = json.loads(board_path.read_text(encoding="utf-8"))
            self.assertEqual([task["id"] for task in board.get("tasks", [])], ["BATCH-01-ANALYSIS"])

    def test_planner_autobatch_skips_when_recent_waiting_sqlite_residue_exists_without_active_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(json.dumps({"items": [], "meta": {}}), encoding="utf-8")
            board_path.write_text(
                json.dumps(
                    {
                        "streams": [],
                        "tasks": [],
                        "events": [],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-88",
                    task_id="BATCH-88-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2999-01-01T00:00:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-88-ADMIN-01", "target_role": "admin"},
                    capability_result={"status": "running", "backend": "codex_exec", "summary": "recent residue"},
                )
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(reason="planner_always_active", cooldown_s=0, source="unit_test")
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_SKIP", out)
            self.assertIn("reason=runtime_truth_residue_active", out)
            self.assertIn("batch_id=BATCH-88", out)
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(queue.get("items", []), [])
            board = json.loads(board_path.read_text(encoding="utf-8"))
            self.assertEqual(board.get("tasks", []), [])

    def test_planner_autobatch_creates_batch_when_runtime_truth_has_no_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(json.dumps({"items": [], "meta": {}}), encoding="utf-8")
            board_path.write_text(
                json.dumps(
                    {
                        "streams": [],
                        "tasks": [],
                        "events": [],
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(reason="planner_always_active", cooldown_s=0, source="unit_test")
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_OK", out)
            self.assertIn("batch_id=BATCH-01", out)
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in queue.get("items", [])], ["BATCH-01"])
            self.assertEqual(queue["items"][0]["state"], "READY")
            board = json.loads(board_path.read_text(encoding="utf-8"))
            self.assertEqual([task["id"] for task in board.get("tasks", [])], ["BATCH-01-ANALYSIS"])
            self.assertEqual(board["tasks"][0]["state"], "READY_PLANNER")

    def test_planner_autobatch_skips_when_runtime_truth_has_live_residue_outside_active_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-89"]},
                        "items": [{"id": "BATCH-89", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            board_path.write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-89"]},
                        "tasks": [{"id": "BATCH-89-ANALYSIS", "stream_id": "BATCH-89", "role": "planner", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-88",
                    task_id="BATCH-88-ADMIN-01",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="admin",
                    status="running",
                    current_node="wait_or_collect_result",
                    updated_at="2999-01-01T00:00:00Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-88-ADMIN-01", "target_role": "admin"},
                    capability_result={"status": "running", "backend": "codex_exec", "summary": "still active"},
                )
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(reason="planner_always_active", cooldown_s=0, source="unit_test")
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_SKIP", out)
            self.assertIn("reason=runtime_truth_residue_active", out)
            self.assertIn("batch_id=BATCH-88", out)
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in queue.get("items", [])], ["BATCH-89"])

    def test_planner_autobatch_creates_queued_batch_while_active_cycle_exists_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-89"]},
                        "items": [{"id": "BATCH-89", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )
            board_path.write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-89"]},
                        "streams": [{"id": "BATCH-89", "state": "IN_PROGRESS"}],
                        "tasks": [{"id": "BATCH-89-DEV-01", "stream_id": "BATCH-89", "role": "dev", "state": "IN_PROGRESS"}],
                        "events": [],
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(
                reason="planner_active_cycle_queue_next",
                cooldown_s=0,
                source="unit_test",
                allow_active_queued=True,
            )
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_OK", out)
            self.assertIn("queued_only=1", out)
            self.assertIn("batch_id=BATCH-90", out)
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in queue.get("items", [])], ["BATCH-89", "BATCH-90"])
            self.assertEqual(queue["items"][1]["state"], "READY")
            self.assertTrue(queue["items"][1]["queued_only"])

    def test_planner_autobatch_ignores_stale_ready_to_merge_residue_without_delivery_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(json.dumps({"items": [], "meta": {}}), encoding="utf-8")
            board_path.write_text(json.dumps({"streams": [], "tasks": [], "events": []}), encoding="utf-8")

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-64",
                    task_id="BATCH-64-DEV-02",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="dev",
                    status="ready_to_merge",
                    current_node="apply_workboard_mutation",
                    updated_at="2026-03-14T03:32:59Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-64-DEV-02", "target_role": "dev"},
                    capability_result={"status": "failed", "backend": "codex_exec", "summary": "historical residue without payload"},
                )
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(reason="planner_always_active", cooldown_s=0, source="unit_test")
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_OK", out)
            self.assertIn("batch_id=BATCH-01", out)

    def test_planner_autobatch_ignores_stale_retryable_residue_without_delivery_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            queue_path = orch / "priority-queue.json"
            board_path = orch / "parallel-workstreams.json"
            queue_path.write_text(json.dumps({"items": [], "meta": {}}), encoding="utf-8")
            board_path.write_text(json.dumps({"streams": [], "tasks": [], "events": []}), encoding="utf-8")

            store = EventStore(root)
            store.upsert_graph_state(
                PlannerGraphState(
                    batch_id="BATCH-63",
                    task_id="BATCH-63-DEV-03",
                    task_kind="runtime",
                    owner_role="planner",
                    target_role="dev",
                    status="retryable",
                    current_node="close_or_requeue",
                    updated_at="2026-03-13T16:15:18Z",
                    engine="langgraph",
                    capability_request={"backend": "codex_exec", "task_id": "BATCH-63-DEV-03", "target_role": "dev"},
                    capability_result={"status": "failed", "backend": "codex_exec", "summary": "historical invalid residue"},
                )
            )

            stdout = io.StringIO()
            args = types.SimpleNamespace(reason="planner_always_active", cooldown_s=0, source="unit_test")
            with redirect_stdout(stdout):
                rc = MODULE._planner_autobatch_cli(root, board_path, queue_path, args)

            self.assertEqual(rc, 0)
            out = stdout.getvalue()
            self.assertIn("AUTOBATCH_OK", out)
            self.assertIn("batch_id=BATCH-01", out)


class PlannerRuntimeActionsPublicProofTests(unittest.TestCase):
    def test_should_run_public_proof_skips_closed_batch_with_ok_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            proof_dir = orch / "public-proof"
            proof_dir.mkdir(parents=True, exist_ok=True)
            (orch / "product_delivery_state.json").write_text(
                json.dumps(
                    {
                        "active_batch_id": None,
                        "last_completed_batch_id": "BATCH-301",
                        "phase": "idle_ready_for_next_batch",
                        "product_done": True,
                        "public_proof_status": "ok",
                    }
                ),
                encoding="utf-8",
            )
            (proof_dir / "BATCH-301.json").write_text(
                json.dumps({"batch_id": "BATCH-301", "status": "ok", "timestamp": "2026-04-16T12:00:00Z"}),
                encoding="utf-8",
            )

            should_run, reason, delivery_state, artifact = MODULE._should_run_public_proof(root)

            self.assertFalse(should_run)
            self.assertEqual(reason, "already_closed_with_public_proof")
            self.assertTrue(delivery_state["product_done"])
            self.assertEqual(artifact["status"], "ok")

    def test_should_run_public_proof_reruns_when_delta_is_newer_than_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            proof_dir = orch / "public-proof"
            proof_dir.mkdir(parents=True, exist_ok=True)
            (orch / "product_delivery_state.json").write_text(
                json.dumps(
                    {
                        "active_batch_id": "BATCH-302",
                        "phase": "verifying_public_proof",
                        "product_done": False,
                        "public_proof_status": "degraded",
                        "last_meaningful_delta_at": "2026-04-16T12:05:00Z",
                    }
                ),
                encoding="utf-8",
            )
            (proof_dir / "BATCH-302.json").write_text(
                json.dumps({"batch_id": "BATCH-302", "status": "ok", "timestamp": "2026-04-16T12:00:00Z"}),
                encoding="utf-8",
            )

            should_run, reason, _, _ = MODULE._should_run_public_proof(root)

            self.assertTrue(should_run)
            self.assertEqual(reason, "new_delivery_delta_after_last_proof")


if __name__ == "__main__":
    unittest.main()
