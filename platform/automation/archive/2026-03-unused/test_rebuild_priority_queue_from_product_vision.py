#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT / "platform" / "automation" / "rebuild_priority_queue_from_product_vision.py"
_SPEC = importlib.util.spec_from_file_location("rebuild_from_vision_local", SCRIPT_PATH)
assert _SPEC and _SPEC.loader
mod = importlib.util.module_from_spec(_SPEC)
sys.modules["rebuild_from_vision_local"] = mod
_SPEC.loader.exec_module(mod)


class RebuildPriorityQueueFromVisionTests(unittest.TestCase):
    def test_parse_vision_batches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vision = Path(td) / "PRODUCT_VISION.md"
            vision.write_text(
                "\n".join(
                    [
                        "### 📋 BATCH-11 — Data Ingestion Core + Freshness SLO (À FAIRE)",
                        "### 📋 BATCH-12 — Portfolio State + Risk Profile Core (À FAIRE)",
                        "### 📋 BATCH-27 — Reliability SRE Pack + Chaos Drills (À FAIRE)",
                    ]
                ),
                encoding="utf-8",
            )
            parsed = mod.parse_vision_batches(vision)
            self.assertEqual([x[0] for x in parsed], ["BATCH-11", "BATCH-12", "BATCH-27"])
            self.assertTrue(parsed[0][1].startswith("Data Ingestion Core"))

    def test_rebuild_strict_order_and_park_out_of_order(self) -> None:
        queue_obj = {
            "items": [
                {"id": "BATCH-10", "title": "old", "state": "CLOSED", "depends_on": ["BATCH-09"]},
                {"id": "BATCH-11", "title": "old", "state": "WAITING_DEP", "depends_on": ["BATCH-10"]},
                {"id": "BATCH-12", "title": "old", "state": "WAITING_DEP", "depends_on": ["BATCH-11"]},
                {"id": "BATCH-27", "title": "old", "state": "IN_PROGRESS", "depends_on": ["BATCH-09"]},
                {"id": "BATCH-28", "title": "old", "state": "WAITING_DEP", "depends_on": ["BATCH-27"]},
            ]
        }
        vision_batches = [
            ("BATCH-10", "Cost/Runtime Governance + Release Gate MVP"),
            ("BATCH-11", "Data Ingestion Core + Freshness SLO"),
            ("BATCH-12", "Portfolio State + Risk Profile Core"),
            ("BATCH-27", "Reliability SRE Pack + Chaos Drills"),
            ("BATCH-28", "MVP v3 Release Gate + Adoption Analytics"),
        ]

        rebuilt, parked, planned, first_open = mod.rebuild_queue(queue_obj, vision_batches)
        by_id = {str(i.get("id")): i for i in rebuilt}

        self.assertEqual(first_open, "BATCH-11")
        self.assertEqual(by_id["BATCH-10"]["state"], "CLOSED")
        self.assertEqual(by_id["BATCH-11"]["state"], "READY")
        self.assertEqual(by_id["BATCH-12"]["state"], "WAITING_DEP")
        self.assertEqual(by_id["BATCH-27"]["state"], "PLANNED")
        self.assertEqual(by_id["BATCH-28"]["state"], "PLANNED")
        self.assertIn("BATCH-27", parked)
        self.assertIn("BATCH-28", planned)
        self.assertTrue(by_id["BATCH-27"].get("parked_by_rebuild"))
        self.assertEqual(by_id["BATCH-12"].get("depends_on"), ["BATCH-11"])

    def test_sync_workboard_for_planned(self) -> None:
        board = {
            "streams": [
                {"id": "BATCH-27", "state": "IN_PROGRESS"},
                {"id": "BATCH-10", "state": "DONE"},
            ],
            "tasks": [
                {"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "state": "IN_PROGRESS", "assignee": "dev"},
                {"id": "BATCH-27-DEV-02", "stream_id": "BATCH-27", "state": "WAITING_DEP", "assignee": ""},
            ],
        }
        streams_updated, tasks_updated = mod.sync_workboard_for_planned(board, ["BATCH-27"], ["BATCH-27"])
        self.assertEqual(streams_updated, 1)
        self.assertEqual(tasks_updated, 2)
        self.assertEqual(board["streams"][0]["state"], "WAITING_DEP")
        self.assertEqual(board["tasks"][0]["state"], "WAITING_DEP")
        self.assertEqual(board["tasks"][0]["assignee"], "")
        self.assertTrue(board["tasks"][0].get("parked_by_rebuild"))

    def test_main_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vision = root / "PRODUCT_VISION.md"
            queue = root / "priority-queue.json"
            workboard = root / "parallel-workstreams.json"

            vision.write_text(
                "\n".join(
                    [
                        "### 📋 BATCH-10 — Cost/Runtime Governance + Release Gate MVP (À FAIRE)",
                        "### 📋 BATCH-11 — Data Ingestion Core + Freshness SLO (À FAIRE)",
                        "### 📋 BATCH-12 — Portfolio State + Risk Profile Core (À FAIRE)",
                        "### 📋 BATCH-27 — Reliability SRE Pack + Chaos Drills (À FAIRE)",
                    ]
                ),
                encoding="utf-8",
            )
            queue.write_text(
                json.dumps(
                    {
                        "items": [
                            {"id": "BATCH-10", "state": "CLOSED", "depends_on": ["BATCH-09"]},
                            {"id": "BATCH-11", "state": "WAITING_DEP", "depends_on": ["BATCH-10"]},
                            {"id": "BATCH-27", "state": "IN_PROGRESS", "depends_on": ["BATCH-09"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            workboard.write_text(
                json.dumps(
                    {
                        "streams": [{"id": "BATCH-27", "state": "IN_PROGRESS"}],
                        "tasks": [{"id": "BATCH-27-DEV-01", "stream_id": "BATCH-27", "state": "IN_PROGRESS"}],
                    }
                ),
                encoding="utf-8",
            )

            rc = mod.main([
                "--vision", str(vision),
                "--queue", str(queue),
                "--workboard", str(workboard),
            ])
            self.assertEqual(rc, 0)
            # Dry-run: original queue file still has BATCH-27 IN_PROGRESS
            dry_queue = json.loads(queue.read_text(encoding="utf-8"))
            self.assertEqual(
                next(i for i in dry_queue["items"] if i["id"] == "BATCH-27")["state"],
                "IN_PROGRESS",
            )

            rc = mod.main([
                "--vision", str(vision),
                "--queue", str(queue),
                "--workboard", str(workboard),
                "--apply",
            ])
            self.assertEqual(rc, 0)
            applied = json.loads(queue.read_text(encoding="utf-8"))
            by_id = {i["id"]: i for i in applied.get("items", [])}
            self.assertEqual(by_id["BATCH-11"]["state"], "READY")
            self.assertEqual(by_id["BATCH-27"]["state"], "PLANNED")


if __name__ == "__main__":
    unittest.main()
