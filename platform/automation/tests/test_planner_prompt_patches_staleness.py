#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "platform" / "automation" / "cron_tmux_role_runner.sh"


class PlannerPromptPatchesStalenessTests(unittest.TestCase):
    def test_runner_ignores_stale_planner_prompt_patches(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('python3 - "$PLANNER_PROMPT_PATCHES_FILE" "$QUEUE_FILE" "$WORKBOARD_FILE"', text)
        self.assertIn("patch_mtime = path.stat().st_mtime if path.exists() else 0.0", text)
        self.assertIn("if source_mtimes and patch_mtime < max(source_mtimes):", text)
        self.assertIn('print("none")', text)


if __name__ == "__main__":
    unittest.main()
