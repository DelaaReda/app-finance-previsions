#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER_SCRIPT = ROOT / "automation" / "cron_tmux_role_runner.sh"


class DevAutonomyEnforcementRunnerTests(unittest.TestCase):
    def test_runner_declares_dev_autonomy_state_file_and_fields(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('DEV_AUTONOMY_STATE_FILE="${STATE_DIR}/dev.autonomy.state.json"', text)
        self.assertIn('"none_no_signal_streak"', text)
        self.assertIn('"last_delivery_ts"', text)
        self.assertIn('"last_enforced_ts"', text)
        self.assertIn('"last_ready_seen_ts"', text)

    def test_runner_preflight_contains_threshold_and_cooldown_guards(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("DEV_AUTONOMY_STALL_THRESHOLD_TICKS", text)
        self.assertIn("DEV_AUTONOMY_ENFORCE_COOLDOWN_SECONDS", text)
        self.assertIn("DEV_AUTONOMY_MAX_ENFORCED_PER_HOUR", text)
        self.assertIn('reason = "none_no_signal_streak_threshold"', text)
        self.assertIn('reason = "cooldown_after_enforce_failures"', text)
        self.assertIn('reason = "max_enforced_per_hour"', text)
        self.assertIn("DEV_AUTONOMY_ENFORCE_GUARD", text)

    def test_runner_enforcement_forces_delivery_contract_when_active(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('values["DELTA"] = "DEV_AUTONOMY_ENFORCED_DELIVERY"', text)
        self.assertIn('kv["dev_autonomy_enforced"] = "1"', text)
        self.assertIn('kv["dev_autonomy_enforce_reason"] = enforce_reason', text)
        self.assertIn('codes.append("dev_autonomy_enforced")', text)
        self.assertIn('NEXT_ACTION_UNIQUE', text)

    def test_runner_enforcement_tracks_fail_streak_and_cooldown(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('state["enforced_fail_streak"]', text)
        self.assertIn('state.get("enforced_timestamps", [])', text)
        self.assertIn('state["cooldown_until_epoch"]', text)
        self.assertIn('state["last_enforced_epoch"]', text)
        self.assertIn('max(0, streak)', text)


if __name__ == "__main__":
    unittest.main()
