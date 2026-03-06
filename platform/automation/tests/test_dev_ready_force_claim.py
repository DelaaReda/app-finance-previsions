#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GUARD = ROOT / "platform" / "policies" / "role_contract_guard.py"
RUNNER = ROOT / "platform" / "automation" / "cron_tmux_role_runner.sh"


class DevReadyForceClaimTests(unittest.TestCase):
    def test_runner_contains_dev_force_claim_contract(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_DEV_FORCE_CLAIM_ON_DEV_READY", text)
        self.assertIn('values["DELTA"] = "DEV_READY_FORCE_CLAIM"', text)
        self.assertIn('values["NEXT"] = "owner=dev; action=claim_or_progress_now"', text)
        self.assertIn('evidence_pairs["dev_wait_allowed"] = "0"', text)
        self.assertIn('evidence_pairs["dev_wait_reason"] = "dev_ready_available"', text)
        self.assertIn('values["DELTA"] = "PLANNER_DISPATCH_INCOMPLETE"', text)
        self.assertIn('values["NEXT"] = "owner=planner; action=repair dispatch ids now"', text)

    def test_contract_guard_autofixes_dev_passive_when_dev_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "dev.contract.txt"
            payload.write_text(
                "\n".join(
                    [
                        "STATUS: WAIT",
                        "DELTA: NO_DELTA",
                        "EVIDENCE: task_update=analysis_only; lock_check=ok; run_note=dev reste en analyse alors que lane actionnable; dev_ready_count=2; dev_ready_task_ids=BATCH-27-DEV-01,BATCH-28-DEV-01; stream_id=none; task_id=none; issues=none; issue_count=0; issue_severity=none",
                        "RISKS: none",
                        "NEXT: owner=dev; action=wait_for_dev_ready_task",
                        "VERDICT: PASS",
                        "BLOCKER_ID: NONE",
                        "NEXT_ACTION_UNIQUE: DEV_NOOP_TEST",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            cp = subprocess.run(
                [
                    "python3",
                    str(GUARD),
                    "dev",
                    "unit_test",
                    str(payload),
                    "1",
                    "1",
                    "0",
                    "queue_v_test",
                    "workboard_v_test",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            out = cp.stdout
            self.assertIn("STATUS: IN_PROGRESS", out)
            self.assertIn("DELTA: DEV_READY_FORCE_CLAIM", out)
            self.assertIn("NEXT: owner=dev; action=claim_or_progress_now", out)
            self.assertIn("dev_non_passive_policy=enforced", out)
            self.assertIn("dev_passive_autofix=1", out)


if __name__ == "__main__":
    unittest.main()
