from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from runtime.truth.lane_backoff import (
    clear_lane_backoff,
    is_lane_backoff_active,
    load_active_lane_backoffs,
    load_lane_backoff,
    write_lane_backoff,
)


class LaneBackoffTests(unittest.TestCase):
    def test_role_only_helpers_use_cwd_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                until = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
                write_lane_backoff(
                    "verifier",
                    {
                        "active": True,
                        "reason": "verifier_no_change_streak",
                        "trigger_streak": 3,
                        "until": until,
                    },
                )

                path = Path(tmpdir) / "logs-codex-runs" / "orchestrator-state" / "lane-backoff" / "verifier.json"
                self.assertTrue(path.exists())
                persisted = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(persisted["role"], "verifier")

                payload = load_lane_backoff("verifier")
                self.assertTrue(is_lane_backoff_active(payload))
                self.assertEqual(payload["trigger_streak"], 3)

                cleared = clear_lane_backoff("verifier", reason="state_changed")
                self.assertFalse(cleared["active"])
                self.assertEqual(cleared["reason"], "state_changed")
            finally:
                os.chdir(cwd)

    def test_load_active_lane_backoffs_filters_expired_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active_until = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
            expired_until = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
            write_lane_backoff(root, "verifier", {"active": True, "until": active_until})
            write_lane_backoff(root, "app-dev", {"active": True, "until": expired_until})

            payload = load_active_lane_backoffs(root)

            self.assertIn("verifier", payload)
            self.assertNotIn("app-dev", payload)


if __name__ == "__main__":
    unittest.main()
