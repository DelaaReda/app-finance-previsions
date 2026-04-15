#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKSTREAM = ROOT / "platform" / "automation" / "compat" / "projections" / "parallel_workstream.py"


class QueueSyncTests(unittest.TestCase):
    def test_sync_priority_uses_task_truth_when_stream_metadata_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "queue sync"},
                "roles": {},
                "streams": [
                    # stale metadata (should be corrected from tasks)
                    {"id": "BATCH-28", "state": "IN_PROGRESS"},
                ],
                "tasks": [
                    {
                        "id": "BATCH-28-PLAN",
                        "stream_id": "BATCH-28",
                        "role": "planner",
                        "priority": "P1",
                        "state": "DONE",
                        "depends_on": [],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                    {
                        "id": "BATCH-28-ARCH",
                        "stream_id": "BATCH-28",
                        "role": "planner",
                        "priority": "P1",
                        "state": "DONE",
                        "depends_on": ["BATCH-28-PLAN"],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                    {
                        "id": "BATCH-28-DEV-01",
                        "stream_id": "BATCH-28",
                        "role": "dev",
                        "priority": "P1",
                        "state": "READY",
                        "depends_on": ["BATCH-28-ARCH"],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-28",
                        "title": "BATCH-28",
                        "state": "IN_PROGRESS",
                        "depends_on": [],
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(queue_after["items"][0]["state"], "READY_DEV")

    def test_sync_priority_updates_in_progress_queue_item_back_to_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "queue sync"},
                "roles": {},
                "streams": [
                    {"id": "BATCH-10", "state": "READY"},
                ],
                "tasks": [
                    {
                        "id": "BATCH-10-PLAN",
                        "stream_id": "BATCH-10",
                        "role": "planner",
                        "priority": "P1",
                        "state": "DONE",
                        "depends_on": [],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                    {
                        "id": "BATCH-10-DEV-01",
                        "stream_id": "BATCH-10",
                        "role": "dev",
                        "priority": "P1",
                        "state": "READY",
                        "depends_on": ["BATCH-10-PLAN"],
                        "created_at": "2026-03-04T00:00:00Z",
                        "updated_at": "2026-03-04T00:00:00Z",
                    },
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-10",
                        "title": "BATCH-10",
                        "state": "IN_PROGRESS",
                        "depends_on": ["BATCH-09"],
                        "next_action": "ouvrir BATCH-10-PLAN",
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            item = queue_after["items"][0]
            self.assertEqual(item["state"], "READY_DEV")
            self.assertEqual(item.get("depends_on"), [])
            self.assertEqual(item.get("legacy_depends_on"), ["BATCH-09"])
            self.assertEqual(item.get("dependency_policy"), "single_batch")
            self.assertTrue(item.get("inter_batch_decoupled_at"))

    def test_sync_priority_decouples_waiting_dep_batch_and_promotes_to_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "queue sync"},
                "roles": {},
                "streams": [],
                "tasks": [],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-11",
                        "title": "BATCH-11",
                        "state": "WAITING_DEP",
                        "depends_on": ["BATCH-10"],
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            item = queue_after["items"][0]
            self.assertEqual(item["state"], "READY_PLANNER")
            self.assertEqual(item.get("depends_on"), [])
            self.assertEqual(item.get("legacy_depends_on"), ["BATCH-10"])

    def test_sanitize_dependencies_decouples_closed_batches_too(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "queue sanitize"},
                "roles": {},
                "streams": [],
                "tasks": [],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-20",
                        "title": "closed batch",
                        "state": "CLOSED",
                        "depends_on": ["BATCH-19"],
                    },
                    {
                        "id": "BATCH-21",
                        "title": "open batch",
                        "state": "WAITING_DEP",
                        "depends_on": ["BATCH-20"],
                    },
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sanitize-dependencies",
                    "--queue",
                    str(queue_path),
                    "--all-batches",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("SANITIZE_OK", cp.stdout)
            self.assertIn("decoupled_total=2", cp.stdout)
            self.assertIn("waiting_dep_reclassified=1", cp.stdout)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            closed_item = queue_after["items"][0]
            open_item = queue_after["items"][1]
            self.assertEqual(closed_item.get("depends_on"), [])
            self.assertEqual(closed_item.get("legacy_depends_on"), ["BATCH-19"])
            self.assertEqual(open_item.get("depends_on"), [])
            self.assertEqual(open_item.get("state"), "PLANNED")

    def test_reconcile_state_updates_non_closed_items_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            board = {
                "version": 1,
                "updated_at": "2026-03-06T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "reconcile"},
                "roles": {},
                "streams": [{"id": "BATCH-40", "state": "READY"}],
                "tasks": [
                    {
                        "id": "BATCH-40-DEV-01",
                        "stream_id": "BATCH-40",
                        "role": "dev",
                        "priority": "P1",
                        "state": "READY",
                        "depends_on": [],
                        "created_at": "2026-03-06T00:00:00Z",
                        "updated_at": "2026-03-06T00:00:00Z",
                    }
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {"id": "BATCH-40", "title": "Batch 40", "state": "WAITING_DEP", "depends_on": []},
                    {"id": "BATCH-41", "title": "Batch 41", "state": "CLOSED", "depends_on": []},
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "reconcile-state",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("RECONCILE_OK", cp.stdout)
            self.assertIn("queue_synced=1", cp.stdout)
            self.assertIn("waiting_dep_reclassified=1", cp.stdout)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertIn(queue_after["items"][0]["state"], {"READY", "READY_DEV", "READY_PLANNER", "IN_PROGRESS"})
            self.assertEqual(queue_after["items"][1]["state"], "CLOSED")

    def test_reconcile_state_normalizes_stale_active_cycle_for_closed_batch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            active_cycle = {
                "cycle_id": "2026-03-13-batch-24-alerting-intelligence-v2",
                "doc_ref": "docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-13.md",
                "dispatch_namespace": "BATCH",
                "active_batch_ids": ["BATCH-24"],
                "recent_completed_batch_ids": ["BATCH-23"],
            }
            board = {
                "version": 1,
                "updated_at": "2026-03-20T00:00:00Z",
                "active_cycle": dict(active_cycle),
                "sprint": {"id": "S-TEST", "goal": "reconcile stale active cycle"},
                "roles": {},
                "streams": [{"id": "BATCH-24", "state": "DONE"}],
                "tasks": [
                    {
                        "id": "BATCH-24-DEV-01",
                        "stream_id": "BATCH-24",
                        "role": "dev",
                        "priority": "P1",
                        "state": "DONE",
                        "depends_on": [],
                        "created_at": "2026-03-20T00:00:00Z",
                        "updated_at": "2026-03-20T00:00:00Z",
                    }
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "updated_at": "2026-03-20T00:00:00Z",
                "active_cycle": dict(active_cycle),
                "items": [
                    {"id": "BATCH-24", "title": "Batch 24", "state": "CLOSED", "depends_on": []},
                ],
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "reconcile-state",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("RECONCILE_OK", cp.stdout)

            board_after = json.loads(board_path.read_text(encoding="utf-8"))
            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))

            self.assertEqual(board_after["active_cycle"]["active_batch_ids"], [])
            self.assertEqual(queue_after["active_cycle"]["active_batch_ids"], [])
            self.assertEqual(
                board_after["active_cycle"]["recent_completed_batch_ids"][:2],
                ["BATCH-24", "BATCH-23"],
            )
            self.assertEqual(
                queue_after["active_cycle"]["recent_completed_batch_ids"][:2],
                ["BATCH-24", "BATCH-23"],
            )

    def test_sync_priority_refreshes_queue_next_action_from_stream_truth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            board = {
                "version": 1,
                "updated_at": "2026-03-06T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "next action sync"},
                "roles": {},
                "streams": [{"id": "BATCH-40", "state": "IN_PROGRESS"}],
                "tasks": [
                    {
                        "id": "BATCH-40-PLAN",
                        "stream_id": "BATCH-40",
                        "code": "PLAN",
                        "role": "planner",
                        "priority": "P1",
                        "state": "DONE",
                    },
                    {
                        "id": "BATCH-40-DEV-01",
                        "stream_id": "BATCH-40",
                        "code": "DEV-01",
                        "role": "dev",
                        "priority": "P1",
                        "state": "READY_DEV",
                        "depends_on": ["BATCH-40-PLAN"],
                    },
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-40",
                        "title": "Batch 40",
                        "state": "IN_PROGRESS",
                        "next_action": "ouvrir BATCH-40-PLAN",
                        "depends_on": [],
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(
                queue_after["items"][0]["next_action"],
                "claim BATCH-40-DEV-01 (READY_DEV pour dev)",
            )

    def test_planner_autobatch_ignores_frontmatter_seed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs_root = root / "docs"
            board_path = docs_root / "operations" / "orchestrator" / "parallel-workstreams.json"
            queue_path = docs_root / "operations" / "orchestrator" / "priority-queue.json"
            board_path.parent.mkdir(parents=True, exist_ok=True)
            (docs_root / "product").mkdir(parents=True, exist_ok=True)
            (docs_root / "product" / "planning").mkdir(parents=True, exist_ok=True)

            board_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "updated_at": "2026-03-08T00:00:00Z",
                        "roles": {},
                        "streams": [],
                        "tasks": [],
                        "handoffs": [],
                        "events": [],
                    },
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(json.dumps({"items": []}, ensure_ascii=True) + "\n", encoding="utf-8")
            (docs_root / "product" / "PRODUCT_VISION.md").write_text(
                "\n".join(
                    [
                        "---",
                        "status: canonical",
                        "---",
                        "# Finance Copilot Product Vision",
                        "",
                        "## One sentence",
                        "Build a personal finance copilot that starts with a brief of the day.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (docs_root / "product" / "planning" / "PRODUCT_VISION.md").write_text(
                "\n".join(
                    [
                        "---",
                        "status: canonical",
                        "---",
                        "# Product Vision Planning Companion",
                        "",
                        "This file is the planning companion for the canonical product vision.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "planner-autobatch",
                    "--queue",
                    str(queue_path),
                    "--reason",
                    "idle_no_ready",
                    "--cooldown-s",
                    "0",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("AUTOBATCH_OK", cp.stdout)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(queue_after["items"][0]["title"], "Build a personal finance copilot that starts with a brief of the day.")
            self.assertNotEqual(queue_after["items"][0]["title"], "status: canonical")

    def test_validate_blocks_when_queue_contains_cross_batch_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "cross dep invariant"},
                "roles": {},
                "streams": [],
                "tasks": [],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-30",
                        "title": "cross dep queue item",
                        "state": "READY",
                        "depends_on": ["BATCH-29"],
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "validate",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 2, msg=cp.stderr)
            self.assertIn("INV-CROSS-DEP-QUEUE", cp.stdout)

    def test_validate_evidence_reports_zero_cross_dep_after_sync(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "cross dep zero"},
                "roles": {},
                "streams": [],
                "tasks": [],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "items": [
                    {
                        "id": "BATCH-31",
                        "title": "dep queue item",
                        "state": "WAITING_DEP",
                        "depends_on": ["BATCH-30"],
                    }
                ]
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp_sync = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp_sync.returncode, 0, msg=cp_sync.stderr)

            cp_validate = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "validate",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp_validate.returncode, 0, msg=cp_validate.stderr)
            self.assertIn("cross_dep_count=0", cp_validate.stdout)
            self.assertIn("queue_inter_batch_dep_count=0", cp_validate.stdout)

    def test_planner_autobatch_creates_ready_batch_stream_and_analysis_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "autobatch"},
                "roles": {},
                "streams": [],
                "tasks": [],
                "handoffs": [],
                "events": [],
            }
            queue = {"version": 1, "updated_at": "2026-03-04T00:00:00Z", "items": [], "meta": {}}
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "planner-autobatch",
                    "--queue",
                    str(queue_path),
                    "--reason",
                    "idle_no_ready",
                    "--cooldown-s",
                    "1800",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("AUTOBATCH_OK", cp.stdout)
            self.assertIn("batch_id=BATCH-01", cp.stdout)

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(queue_after["items"][0]["id"], "BATCH-01")
            self.assertEqual(queue_after["items"][0].get("depends_on"), [])
            self.assertEqual(queue_after["items"][0].get("next_action"), "ouvrir BATCH-01-ANALYSIS")

            board_after = json.loads(board_path.read_text(encoding="utf-8"))
            stream_ids = {str(s.get("id")) for s in board_after.get("streams", [])}
            self.assertIn("BATCH-01", stream_ids)
            analysis_tasks = [
                t for t in board_after.get("tasks", [])
                if str(t.get("id", "")).strip() == "BATCH-01-ANALYSIS"
            ]
            self.assertEqual(len(analysis_tasks), 1)
            self.assertEqual(str(analysis_tasks[0].get("state", "")).upper(), "READY_PLANNER")
            self.assertEqual(str(analysis_tasks[0].get("role", "")).lower(), "planner")

    def test_sync_priority_preserves_autobatch_analysis_without_backfilling_upstream_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-04-15T03:46:45Z",
                "sprint": {"id": "S-TEST", "goal": "autobatch preserve"},
                "roles": {"planner": {"wip_limit": 1, "can_edit": False, "focus": "planning"}},
                "streams": [
                    {
                        "id": "BATCH-85",
                        "title": "BATCH-85",
                        "priority": "P2",
                        "source_state": "READY",
                        "state": "IN_PROGRESS",
                        "created_at": "2026-04-15T03:46:32Z",
                        "updated_at": "2026-04-15T03:46:45Z",
                    }
                ],
                "tasks": [
                    {
                        "id": "BATCH-85-ANALYSIS",
                        "stream_id": "BATCH-85",
                        "code": "ANALYSIS",
                        "title": "BATCH-85 [ANALYSIS]",
                        "role": "planner",
                        "state": "IN_PROGRESS",
                        "status": "IN_PROGRESS",
                        "priority": "P2",
                        "depends_on": [],
                        "assignee": "planner",
                        "blocked_reason": "",
                        "artifacts": [],
                        "notes": [
                            "AUTOBATCH-NOTE: generated by planner-autobatch to keep planner lane non-passive."
                        ],
                        "handoff_to": "",
                        "created_at": "2026-04-15T03:46:32Z",
                        "updated_at": "2026-04-15T03:46:45Z",
                        "started_at": "2026-04-15T03:46:45Z",
                        "completed_at": "",
                    }
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "version": 1,
                "updated_at": "2026-04-15T03:49:05Z",
                "items": [
                    {
                        "id": "BATCH-85",
                        "title": "BATCH-85",
                        "state": "READY",
                        "priority": "P2",
                        "owner_role": "planner",
                        "created_by": "planner_autonomy",
                        "vision_ref": "docs/product/PRODUCT_VISION.md#One sentence",
                        "scope_key": "batch-85",
                        "novelty_class": "net_new",
                        "delivery_kind": "net_new",
                        "user_value_delta_visible": 1,
                        "next_action": "ouvrir BATCH-85-ANALYSIS",
                        "depends_on": [],
                        "dependency_policy": "single_batch",
                        "created_at": "2026-04-15T03:46:32Z",
                        "updated_at": "2026-04-15T03:49:05Z",
                    }
                ],
                "meta": {},
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            board_after = json.loads(board_path.read_text(encoding="utf-8"))
            task_ids = {str(task.get("id", "")) for task in board_after.get("tasks", [])}
            self.assertNotIn("BATCH-85-PLAN", task_ids)

            analysis = next(task for task in board_after.get("tasks", []) if str(task.get("id", "")) == "BATCH-85-ANALYSIS")
            self.assertEqual(analysis.get("depends_on"), [])
            self.assertEqual(str(analysis.get("state", "")).upper(), "IN_PROGRESS")

            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertIn("BATCH-85-ANALYSIS", queue_after["items"][0].get("next_action", ""))

    def test_planner_autobatch_reuses_duplicate_title_batch_nonfatally(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs_root = root / "docs"
            board_path = docs_root / "operations" / "orchestrator" / "parallel-workstreams.json"
            queue_path = docs_root / "operations" / "orchestrator" / "priority-queue.json"
            board_path.parent.mkdir(parents=True, exist_ok=True)
            (docs_root / "product").mkdir(parents=True, exist_ok=True)

            board_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "updated_at": "2026-03-08T00:00:00Z",
                        "roles": {},
                        "streams": [],
                        "tasks": [],
                        "handoffs": [],
                        "events": [],
                    },
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "items": [
                            {
                                "id": "BATCH-40",
                                "title": "Build a personal finance copilot that starts with a brief of the day.",
                                "state": "READY",
                            }
                        ],
                    },
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (docs_root / "product" / "PRODUCT_VISION.md").write_text(
                "\n".join(
                    [
                        "# Finance Copilot Product Vision",
                        "",
                        "Build a personal finance copilot that starts with a brief of the day.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "planner-autobatch",
                    "--queue",
                    str(queue_path),
                    "--reason",
                    "idle_no_ready",
                    "--cooldown-s",
                    "0",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("AUTOBATCH_OK", cp.stdout)
            self.assertIn("batch_id=BATCH-40", cp.stdout)

            board_after = json.loads(board_path.read_text(encoding="utf-8"))
            stream_ids = {str(s.get("id")) for s in board_after.get("streams", [])}
            self.assertIn("BATCH-40", stream_ids)
            task_ids = {str(t.get("id")) for t in board_after.get("tasks", [])}
            self.assertIn("BATCH-40-ANALYSIS", task_ids)
            self.assertTrue(
                any(str(event.get("kind", "")) == "planner_autobatch_reused" for event in board_after.get("events", []))
            )

    def test_planner_autobatch_skips_when_runway_is_not_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "roles": {},
                "streams": [{"id": "BATCH-02", "state": "BLOCKED", "updated_at": "2026-03-04T00:00:00Z"}],
                "tasks": [
                    {
                        "id": "BATCH-02-ADMIN-01",
                        "stream_id": "BATCH-02",
                        "role": "admin",
                        "state": "BLOCKED",
                        "updated_at": "2026-03-04T00:00:00Z",
                    }
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {"version": 1, "updated_at": "2026-03-04T00:00:00Z", "items": [], "meta": {}}
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "planner-autobatch",
                    "--queue",
                    str(queue_path),
                    "--reason",
                    "idle_no_ready",
                    "--cooldown-s",
                    "0",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("AUTOBATCH_SKIP", cp.stdout)
            self.assertIn("reason=runway_not_empty", cp.stdout)

    def test_planner_autobatch_skips_when_cooldown_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"
            board = {
                "version": 1,
                "updated_at": "2026-03-04T00:00:00Z",
                "sprint": {"id": "S-TEST", "goal": "autobatch cooldown"},
                "roles": {},
                "streams": [],
                "tasks": [],
                "handoffs": [],
                "events": [
                    {
                        "at": "2099-01-01T00:00:00Z",
                        "kind": "planner_autobatch_created",
                        "details": {"batch_id": "BATCH-98"},
                    }
                ],
            }
            queue = {"version": 1, "updated_at": "2026-03-04T00:00:00Z", "items": [], "meta": {}}
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "planner-autobatch",
                    "--queue",
                    str(queue_path),
                    "--cooldown-s",
                    "1800",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("AUTOBATCH_SKIP", cp.stdout)
            self.assertIn("reason=cooldown", cp.stdout)

    def test_sync_priority_closes_stale_upstream_task_when_downstream_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            queue_path = Path(td) / "priority-queue.json"

            board = {
                "version": 1,
                "updated_at": "2026-04-15T04:30:29Z",
                "roles": {},
                "streams": [
                    {
                        "id": "BATCH-85",
                        "state": "IN_PROGRESS",
                        "next_action": "compléter BATCH-85-ANALYSIS (READY_PLANNER pour planner)",
                    }
                ],
                "tasks": [
                    {
                        "id": "BATCH-85-ANALYSIS",
                        "stream_id": "BATCH-85",
                        "code": "ANALYSIS",
                        "role": "planner",
                        "state": "IN_PROGRESS",
                        "status": "IN_PROGRESS",
                        "depends_on": [],
                        "started_at": "2026-04-15T04:13:51Z",
                        "completed_at": "",
                        "created_at": "2026-04-15T03:46:32Z",
                        "updated_at": "2026-04-15T04:32:18Z",
                    },
                    {
                        "id": "BATCH-85-ARCH",
                        "stream_id": "BATCH-85",
                        "code": "ARCH",
                        "role": "planner",
                        "state": "DONE",
                        "status": "DONE",
                        "depends_on": ["BATCH-85-ANALYSIS"],
                        "started_at": "2026-04-15T04:20:00Z",
                        "completed_at": "2026-04-15T04:24:00Z",
                        "created_at": "2026-04-15T03:46:32Z",
                        "updated_at": "2026-04-15T04:24:00Z",
                    },
                    {
                        "id": "BATCH-85-DEV-01",
                        "stream_id": "BATCH-85",
                        "code": "DEV-01",
                        "role": "dev",
                        "state": "IN_PROGRESS",
                        "status": "IN_PROGRESS",
                        "depends_on": ["BATCH-85-ARCH"],
                        "started_at": "2026-04-15T04:30:29Z",
                        "completed_at": "",
                        "created_at": "2026-04-15T03:46:32Z",
                        "updated_at": "2026-04-15T04:30:29Z",
                    },
                ],
                "handoffs": [],
                "events": [],
            }
            queue = {
                "version": 1,
                "updated_at": "2026-04-15T04:32:18Z",
                "items": [
                    {
                        "id": "BATCH-85",
                        "title": "BATCH-85",
                        "state": "IN_PROGRESS",
                        "priority": "P2",
                        "next_action": "compléter BATCH-85-ANALYSIS (READY_PLANNER pour planner)",
                        "depends_on": [],
                    }
                ],
                "meta": {},
            }
            board_path.write_text(json.dumps(board, ensure_ascii=True) + "\n", encoding="utf-8")
            queue_path.write_text(json.dumps(queue, ensure_ascii=True) + "\n", encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(WORKSTREAM),
                    "--board",
                    str(board_path),
                    "sync-priority",
                    "--queue",
                    str(queue_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            board_after = json.loads(board_path.read_text(encoding="utf-8"))
            analysis = next(task for task in board_after["tasks"] if task["id"] == "BATCH-85-ANALYSIS")
            stream = next(item for item in board_after["streams"] if item["id"] == "BATCH-85")
            queue_after = json.loads(queue_path.read_text(encoding="utf-8"))

            self.assertEqual(analysis["state"], "DONE")
            self.assertTrue(analysis["completed_at"])
            self.assertEqual(stream["next_action"], "compléter BATCH-85-DEV-01 (READY_PLANNER pour dev)")
            self.assertEqual(queue_after["items"][0]["next_action"], "compléter BATCH-85-DEV-01 (READY_PLANNER pour dev)")


if __name__ == "__main__":
    unittest.main()
