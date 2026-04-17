from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from apps.monitor.services import status_service


class StatusServiceAppOnlyDeliveryControlTests(unittest.TestCase):
    def test_app_only_host_prefers_live_runtime_truth_delivery_state(self) -> None:
        stale_delivery_state = {
            "schema_version": "product_delivery_state.v1",
            "active_batch_id": None,
            "phase": "external_outage",
            "product_done": False,
            "ops_clean": True,
            "public_proof_status": "error",
            "user_visible_delta_confirmed": False,
            "next_batch_eligible": False,
            "ec2_reachable": False,
            "freeze_reason": "external_outage",
            "current_public_proof": {"batch_id": None, "status": "none"},
            "current_value_target": {"batch_id": None, "novelty_target": None, "user_visible_delta": None},
            "maintenance_active": False,
            "maintenance_reason": "none",
            "maintenance_command": "",
            "maintenance_age_s": None,
            "maintenance_source": "remote_runtime_lock_meta",
            "last_meaningful_delta_at": None,
            "last_public_proof_ok_at": None,
            "last_completed_batch_id": None,
            "last_closed_at": None,
            "last_completion_proof_ref": None,
            "close_reason": "none",
            "advisory_mismatch": [],
            "generated_at": "2026-04-17T03:21:46.512798Z",
        }
        live_delivery_state = {
            "schema_version": "product_delivery_state.v1",
            "active_batch_id": None,
            "phase": "idle_ready_for_next_batch",
            "product_done": False,
            "ops_clean": True,
            "public_proof_status": "ok",
            "user_visible_delta_confirmed": False,
            "next_batch_eligible": True,
            "ec2_reachable": True,
            "freeze_reason": "none",
            "current_public_proof": {"batch_id": None, "status": "none"},
            "current_value_target": {"batch_id": None, "novelty_target": None, "user_visible_delta": None},
            "maintenance_active": False,
            "maintenance_reason": "none",
            "maintenance_command": "",
            "maintenance_age_s": None,
            "maintenance_source": "none",
            "last_meaningful_delta_at": None,
            "last_public_proof_ok_at": None,
            "last_completed_batch_id": None,
            "last_closed_at": None,
            "last_completion_proof_ref": None,
            "close_reason": "none",
            "advisory_mismatch": [],
            "generated_at": "2026-04-17T03:22:12.000000Z",
        }

        payload = {
            "doctor": {
                "status": "error",
                "overall_status": "error",
                "checks": {
                    "providers": {
                        "api_reachable_effective": True,
                        "api_health_ok": True,
                        "api_base": "http://3.98.20.77",
                    }
                },
            },
            "monitor_host": {
                "profile": "app_only",
                "control_plane_location": "remote_vm",
            },
            "runtime_state": {
                "execution_mode": "planner_experimental",
            },
        }

        with mock.patch.object(
            status_service,
            "probe_public_surface",
            return_value={"http_ok": True, "maintenance_active": False},
        ), mock.patch.object(
            status_service,
            "_probe_http_ok",
            return_value=True,
        ), mock.patch.object(
            status_service,
            "build_runtime_truth_snapshot",
            return_value={
                "event_store_primary": False,
                "product_delivery_state": live_delivery_state,
            },
        ), mock.patch.object(
            status_service,
            "load_product_delivery_state",
            return_value=stale_delivery_state,
        ), mock.patch.object(
            status_service,
            "collect_queue_workboard",
            return_value={"queue": {"items": [], "active_cycle": {}}},
        ), mock.patch.object(
            status_service,
            "build_plane_planning_snapshot",
            return_value={},
        ):
            result = status_service.build_status_snapshot(
                ROOT,
                lambda: payload,
                include_layers=False,
            )

        self.assertEqual(result["delivery_control"]["phase"], "idle_ready_for_next_batch")
        self.assertTrue(result["delivery_control"]["ec2_reachable"])
        self.assertEqual(result["delivery_control"]["freeze_reason"], "none")
        self.assertTrue(result["delivery_control"]["next_batch_eligible"])
        self.assertEqual(result["product_runtime"]["status"], "ok")
        self.assertTrue(result["agentic_runtime"]["advisory_only"])


if __name__ == "__main__":
    unittest.main()
