from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from runtime.truth.verifier_governor import (
    load_verifier_state,
    persist_verifier_state,
    should_run_verifier,
)


class VerifierGovernorTests(unittest.TestCase):
    def test_should_run_verifier_only_on_change(self) -> None:
        delivery_state = {
            "active_batch_id": "BATCH-101",
            "phase": "verifying_public_proof",
            "product_done": False,
            "public_proof_status": "degraded",
            "last_meaningful_delta_at": "2026-04-16T12:00:00Z",
            "current_public_proof": {"batch_id": "BATCH-101", "proof_ref": None},
            "current_value_target": {"batch_id": "BATCH-101", "user_visible_delta": "ranked action visible"},
        }

        decision = should_run_verifier(delivery_state, {})
        self.assertTrue(decision["should_run"])
        self.assertEqual(decision["reason"], "new_batch")

        verifier_state = {
            "last_batch_id": "BATCH-101",
            "last_status": "error",
            "last_trigger_fingerprint": decision["trigger_fingerprint"],
        }
        noop = should_run_verifier(delivery_state, verifier_state)
        self.assertFalse(noop["should_run"])
        self.assertEqual(noop["reason"], "no_change")

        error_state = dict(delivery_state)
        error_state["public_proof_status"] = "error"
        error_decision = should_run_verifier(error_state, {})
        error_verifier_state = {
            "last_batch_id": "BATCH-101",
            "last_status": "error",
            "last_trigger_fingerprint": error_decision["trigger_fingerprint"],
        }
        no_retry = should_run_verifier(error_state, error_verifier_state)
        self.assertFalse(no_retry["should_run"])
        self.assertEqual(no_retry["reason"], "public_proof_error_no_new_delta")

        changed_state = dict(delivery_state)
        changed_state["last_meaningful_delta_at"] = "2026-04-16T12:05:00Z"
        rerun = should_run_verifier(changed_state, verifier_state)
        self.assertTrue(rerun["should_run"])
        self.assertEqual(rerun["reason"], "state_changed")

    def test_persist_verifier_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            persist_verifier_state(
                root,
                {
                    "last_batch_id": "BATCH-202",
                    "last_status": "ok",
                    "last_trigger_fingerprint": '{"active_batch_id":"BATCH-202"}',
                },
            )

            payload = load_verifier_state(root)

            self.assertEqual(payload["last_batch_id"], "BATCH-202")
            self.assertEqual(payload["last_status"], "ok")
            self.assertIn("updated_at", payload)

    def test_api_wave_verifier_runs_once_per_endpoint_change(self) -> None:
        delivery_state = {
            "active_batch_id": "BATCH-API-WAVE-01",
            "phase": "verifying_public_proof",
            "product_done": False,
            "public_proof_status": "degraded",
            "last_meaningful_delta_at": "2026-04-16T12:00:00Z",
            "current_public_proof": {"batch_id": "BATCH-API-WAVE-01", "endpoint_id": "copilot.search", "proof_ref": None},
            "current_value_target": {"batch_id": "BATCH-API-WAVE-01", "endpoint_id": "copilot.search"},
            "api_autonomy_mode": True,
            "api_wave": {
                "wave_batch_id": "BATCH-API-WAVE-01",
                "current_endpoint_id": "copilot.search",
                "current_status": "verifying_public_proof",
                "current_proof_status": "degraded",
                "last_public_proof_ref": "none",
            },
        }

        first = should_run_verifier(delivery_state, {})
        self.assertTrue(first["should_run"])
        self.assertEqual(first["endpoint_id"], "copilot.search")

        verifier_state = {
            "last_batch_id": "BATCH-API-WAVE-01",
            "last_endpoint_id": "copilot.search",
            "last_status": "error",
            "last_trigger_fingerprint": first["trigger_fingerprint"],
        }
        second = should_run_verifier(delivery_state, verifier_state)
        self.assertFalse(second["should_run"])
        self.assertEqual(second["reason"], "no_change")

        changed = dict(delivery_state)
        changed["api_wave"] = dict(delivery_state["api_wave"], current_endpoint_id="copilot.universal_search")
        changed["current_public_proof"] = {"batch_id": "BATCH-API-WAVE-01", "endpoint_id": "copilot.universal_search", "proof_ref": None}
        changed["current_value_target"] = {"batch_id": "BATCH-API-WAVE-01", "endpoint_id": "copilot.universal_search"}
        rerun = should_run_verifier(changed, verifier_state)
        self.assertTrue(rerun["should_run"])
        self.assertEqual(rerun["reason"], "new_batch")


if __name__ == "__main__":
    unittest.main()
