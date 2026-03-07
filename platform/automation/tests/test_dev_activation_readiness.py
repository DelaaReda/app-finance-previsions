from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "platform" / "automation" / "dev_activation_readiness.py"
SPEC = importlib.util.spec_from_file_location("fc_dev_activation_readiness", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DevActivationReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_build_readiness_blocks_on_news_stale_and_dispatch_pressure(self) -> None:
        status_payload = {
            "runtime_state": {"lifecycle": "running"},
            "execution_mode": "planner_experimental",
            "delivery_integrity": {"status": "ok"},
            "product_value_metrics": {
                "priority_guard": {
                    "status": "blocked",
                    "blocked_reasons": ["news_stale"],
                }
            },
            "planner_dispatch": {
                "status": "degraded",
                "ready_dev_count": 3,
                "active_subagents": 0,
                "needs_dispatch": True,
                "stalled_ready_dev": True,
                "recent_fallback_like_count": 1,
                "recent_failed_count": 0,
            },
        }
        doctor_payload = {"status": "ok"}

        with mock.patch.object(
            MODULE,
            "_probe_json",
            side_effect=[(status_payload, ""), (doctor_payload, "")],
        ), mock.patch.object(
            MODULE,
            "_validate_bridge",
            return_value=({"ok": True, "bridge_validation": {"ok": True}}, ""),
        ):
            payload = MODULE.build_readiness(self.root)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("news_stale", payload["blockers"])
        self.assertIn("planner_dispatch_needed", payload["blockers"])
        self.assertIn("ready_dev_stalled", payload["blockers"])
        self.assertIn("recent_dispatch_fallback_like", payload["blockers"])
        self.assertEqual(payload["checks"]["openclaw_bridge"]["status"], "ok")

    def test_build_readiness_is_ok_when_runtime_bridge_and_product_are_green(self) -> None:
        status_payload = {
            "runtime_state": {"lifecycle": "running"},
            "execution_mode": "planner_experimental",
            "delivery_integrity": {"status": "ok"},
            "product_value_metrics": {
                "priority_guard": {
                    "status": "ok",
                    "blocked_reasons": [],
                }
            },
            "planner_dispatch": {
                "status": "ok",
                "ready_dev_count": 0,
                "active_subagents": 1,
                "needs_dispatch": False,
                "stalled_ready_dev": False,
                "recent_fallback_like_count": 0,
                "recent_failed_count": 0,
            },
        }
        doctor_payload = {"status": "ok"}

        with mock.patch.object(
            MODULE,
            "_probe_json",
            side_effect=[(status_payload, ""), (doctor_payload, "")],
        ), mock.patch.object(
            MODULE,
            "_validate_bridge",
            return_value=({"ok": True, "bridge_validation": {"ok": True}}, ""),
        ):
            payload = MODULE.build_readiness(self.root)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["blockers"], [])


if __name__ == "__main__":
    unittest.main()
