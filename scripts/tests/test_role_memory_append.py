#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPENDER = ROOT / "scripts" / "role_memory_append.py"


class RoleMemoryAppendTests(unittest.TestCase):
    def test_appends_compact_line_and_creates_header(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DEV_BATCH02_PROGRESS",
                (
                    "EVIDENCE: stream_id=BATCH-02; task_id=BATCH-02-DEV; "
                    "exec_report=patch_applied; issues=none; suggestions=none"
                ),
                "RISKS: none",
                "NEXT: owner=tester; action=run_tests",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_NEXT",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload_file = root / "payload.txt"
            mem_file = root / "memory" / "dev.md"
            lock_file = root / "state" / "dev.memory.lock"
            payload_file.write_text(payload, encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(APPENDER),
                    "dev",
                    "unit_test",
                    str(payload_file),
                    str(mem_file),
                    str(lock_file),
                    "2026-02-27 10:00:00 EST",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            text = mem_file.read_text(encoding="utf-8")
            self.assertIn("# dev", text)
            self.assertIn("role=dev source=unit_test status=IN_PROGRESS", text)
            self.assertIn("stream_id=BATCH-02", text)
            self.assertIn("task_id=BATCH-02-DEV", text)

    def test_trims_large_memory_file(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DEV_BATCH02_PROGRESS",
                "EVIDENCE: stream_id=BATCH-02; task_id=BATCH-02-DEV; exec_report=patch_applied; issues=none; suggestions=none",
                "RISKS: none",
                "NEXT: owner=tester; action=run_tests",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_NEXT",
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload_file = root / "payload.txt"
            mem_file = root / "memory" / "dev.md"
            lock_file = root / "state" / "dev.memory.lock"
            mem_file.parent.mkdir(parents=True, exist_ok=True)
            pre_lines = ["# dev\n", "\n"] + [f"- old line {idx}\n" for idx in range(920)]
            mem_file.write_text("".join(pre_lines), encoding="utf-8")
            payload_file.write_text(payload, encoding="utf-8")

            cp = subprocess.run(
                [
                    sys.executable,
                    str(APPENDER),
                    "dev",
                    "unit_test_trim",
                    str(payload_file),
                    str(mem_file),
                    str(lock_file),
                    "2026-02-27 10:10:00 EST",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            lines = mem_file.read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(lines), 810)
            self.assertIn("unit_test_trim", mem_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
