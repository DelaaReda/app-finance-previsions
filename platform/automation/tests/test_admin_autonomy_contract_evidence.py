#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "platform" / "automation" / "cron_tmux_role_runner.sh"


class AdminAutonomyContractEvidenceTests(unittest.TestCase):
    def test_runner_includes_admin_autonomy_evidence_fields(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("admin_autonomy_refresh_state_if_needed()", text)
        self.assertIn("ADMIN_AUTONOMY_STATE_FILE", text)
        self.assertIn("admin_autonomy_trigger", text)
        self.assertIn("admin_autonomy_target_role", text)
        self.assertIn("admin_autonomy_target_task", text)
        self.assertIn("admin_autonomy_action_seq", text)
        self.assertIn("admin_autonomy_proof_gate", text)
        self.assertIn("admin_autonomy_outcome", text)
        self.assertIn("admin_autonomy_evidence_missing", text)


if __name__ == "__main__":
    unittest.main()
