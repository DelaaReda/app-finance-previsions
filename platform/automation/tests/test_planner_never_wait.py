#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "automation" / "cron_tmux_role_runner.sh"


class PlannerNeverWaitContractTests(unittest.TestCase):
    def test_runner_contains_planner_never_wait_enforcement(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('TMUX_ROLE_PLANNER_NEVER_WAIT="${TMUX_ROLE_PLANNER_NEVER_WAIT:-1}"', text)
        self.assertIn('values["DELTA"] = "PLANNER_AUTONOMY_ENFORCED"', text)
        self.assertIn('values["NEXT"] = "owner=planner; action=create_or_claim_now"', text)
        self.assertIn('append_issue("planner_passivity_corrected")', text)

    def test_planner_prompt_requires_create_or_claim(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"ROLE=planner\.(.*?)PROMPT", text, flags=re.S)
        self.assertIsNotNone(m)
        block = m.group(1)
        self.assertIn("créer immédiatement 1 batch top-level", block)
        self.assertNotIn("sinon task_update=none_no_ready", block)


if __name__ == "__main__":
    unittest.main()
