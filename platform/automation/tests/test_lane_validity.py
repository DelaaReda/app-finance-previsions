#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "lane_validity.py"
_SPEC = importlib.util.spec_from_file_location("lane_validity_local", MODULE_PATH)
assert _SPEC and _SPEC.loader
lane_validity = importlib.util.module_from_spec(_SPEC)
sys.modules["lane_validity_local"] = lane_validity
_SPEC.loader.exec_module(lane_validity)


class LaneValidityTests(unittest.TestCase):
    def test_contract_fields_extract_inline_stream_and_task_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "planner.last_contract"
            path.write_text(
                "\n".join(
                    [
                        "STATUS: IN_PROGRESS",
                        (
                            "EVIDENCE: task_update=claim; stream_id=BATCH-94; "
                            "task_id=BATCH-94-ARCH; planner_quality_score=0"
                        ),
                        "VERDICT: GO_WITH_CAUTION",
                    ]
                ),
                encoding="utf-8",
            )
            fields = lane_validity._contract_fields(path)

        self.assertEqual(fields.get("STREAM_ID"), "BATCH-94")
        self.assertEqual(fields.get("TASK_ID"), "BATCH-94-ARCH")
        self.assertEqual(fields.get("BATCH_ID"), "BATCH-94")


if __name__ == "__main__":
    unittest.main()
