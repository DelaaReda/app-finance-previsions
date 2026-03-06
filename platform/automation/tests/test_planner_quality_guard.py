#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GUARD = ROOT / "platform" / "policies" / "role_contract_guard.py"


def _parse_contract(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in str(raw or "").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().upper()
        if key and key not in out:
            out[key] = v.strip()
    return out


class PlannerQualityGuardTests(unittest.TestCase):
    def _run_guard(self, payload: str, env: dict[str, str] | None = None) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as td:
            payload_file = Path(td) / "payload.txt"
            payload_file.write_text(payload, encoding="utf-8")
            merged_env = None
            if env:
                import os
                merged_env = os.environ.copy()
                merged_env.update(env)
            cp = subprocess.run(
                [
                    "python3",
                    str(GUARD),
                    "planner",
                    "primary",
                    str(payload_file),
                    "1",
                    "1",
                    "1",
                    "qv-test",
                    "wv-test",
                ],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
                env=merged_env,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            return _parse_contract(cp.stdout)

    def test_claim_incomplete_is_go_with_caution_not_hard_block(self) -> None:
        payload = """STATUS: IN_PROGRESS
DELTA: NO_DELTA
EVIDENCE: task_update=claim; lock_check=ok; run_note=planner claim quality test with minimal evidence; stream_id=BATCH-55-PLAN; task_id=BATCH-55-PLAN-01; planner_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md; issues=none; issue_count=0; issue_severity=none
RISKS: quality pending
NEXT: owner=planner; action=claim now
VERDICT: GO
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: PLANNER_QUALITY_CLAIM_TEST
"""
        values = self._run_guard(payload)
        self.assertEqual(values.get("BLOCKER_ID"), "NONE")
        self.assertEqual(values.get("VERDICT"), "GO_WITH_CAUTION")
        self.assertIn("planner_quality_missing=", values.get("EVIDENCE", ""))

    def test_complete_missing_verify_is_soft_non_blocking(self) -> None:
        payload = """STATUS: IN_PROGRESS
DELTA: DELIVERY
EVIDENCE: task_update=complete; lock_check=ok; run_note=planner complete quality test includes evidence markers; stream_id=BATCH-55-PLAN; task_id=BATCH-55-PLAN-01; cmd=python3 -m pytest -q; root_cause=deps mismatch identified on queue/workboard; fix_applied=reconciled queue/workboard states; reuse_check=platform.automation.parallel_workstream; vision_alignment=batch=BATCH-55; target=reliability; impact=high; planner_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md; issues=none; issue_count=0; issue_severity=none
RISKS: low
NEXT: owner=planner; action=handoff to dev
VERDICT: GO
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: PLANNER_QUALITY_COMPLETE_TEST
"""
        values = self._run_guard(payload, env={"PLANNER_QUALITY_SOFT_ENFORCE": "0"})
        self.assertEqual(values.get("BLOCKER_ID"), "NONE")
        self.assertEqual(values.get("VERDICT"), "GO_WITH_CAUTION")
        self.assertEqual(values.get("STATUS"), "IN_PROGRESS")
        self.assertIn("planner_evidence_incomplete_soft", values.get("EVIDENCE", ""))


if __name__ == "__main__":
    unittest.main()
