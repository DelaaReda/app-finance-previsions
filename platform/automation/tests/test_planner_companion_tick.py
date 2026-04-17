#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "planner_companion_tick.sh"


class PlannerCompanionTickTests(unittest.TestCase):
    def test_runtime_idle_overrides_stale_guardian_issues(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("snapshot_no_actionable_work = (", text)
        self.assertIn("guardian_runtime_idle_override = snapshot_no_actionable_work and bool(issues)", text)
        self.assertIn('guardian_level = "idle"', text)
        self.assertIn('"guardian_runtime_idle_override": int(guardian_runtime_idle_override)', text)

    def test_reads_canonical_downstream_summary(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('canonical_active_task_id = str(summary.get("canonical_active_task_id") or "").strip()', text)
        self.assertIn('canonical_active_task_role = str(summary.get("canonical_active_task_role") or "").strip().lower()', text)
        self.assertIn('canonical_downstream_active = bool(', text)

    def test_collect_message_wins_when_downstream_task_is_active(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("Collect via planner_subagent_manager.py collect", text)
        self.assertIn("Pas de claim planner, pas d analysis_only, pas de planner-autobatch", text)
        self.assertIn('reason = "canonical_downstream_requires_collect"', text)


if __name__ == "__main__":
    unittest.main()
