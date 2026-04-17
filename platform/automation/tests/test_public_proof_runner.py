from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from runtime.truth.public_proof_runner import run_public_proof
from runtime.truth.runtime_truth_reader import persist_product_delivery_state


class PublicProofRunnerTests(unittest.TestCase):
    def test_run_public_proof_uses_canonical_batch_and_persists_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "BATCH-01",
                                "delivery_contract": {
                                    "value_target": "portfolio_first_brief",
                                    "user_visible_delta": "top action visible",
                                    "api_proof": {
                                        "base_url": "http://3.98.20.77",
                                        "expected_endpoints": ["/api/health", "/api/copilot/start"],
                                    },
                                    "ui_proof": {"url": "http://3.98.20.77/"},
                                    "done_when": "public_proof_status=ok && user_visible_delta_confirmed=true",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(json.dumps({"streams": [], "tasks": []}), encoding="utf-8")
            persist_product_delivery_state(
                root,
                {
                    "schema_version": "product_delivery_state.v1",
                    "active_batch_id": "BATCH-01",
                    "phase": "verifying_public_proof",
                    "product_done": False,
                    "ops_clean": False,
                    "public_proof_status": "degraded",
                    "user_visible_delta_confirmed": False,
                    "next_batch_eligible": False,
                    "ec2_reachable": True,
                    "freeze_reason": "waiting_public_proof",
                },
            )

            def fake_probe(url: str, **_: object) -> dict[str, object]:
                return {
                    "url": url,
                    "http_ok": True,
                    "http_status": 200,
                    "effective_state": "ok",
                    "maintenance_active": False,
                }

            with mock.patch("runtime.truth.public_proof_runner.probe_public_surface", side_effect=fake_probe), mock.patch(
                "runtime.truth.public_proof_runner.run_browser_smoke",
                return_value={"proof_path": str(root / "browser-proof.json"), "screenshot_copy": str(root / "browser-proof.png")},
            ):
                artifact = run_public_proof(root)

            self.assertEqual(artifact["batch_id"], "BATCH-01")
            self.assertEqual(artifact["status"], "ok")
            self.assertTrue(artifact["user_visible_delta_confirmed"])
            self.assertEqual(artifact["api_smoke_status"], "ok")
            self.assertEqual(artifact["ui_smoke_status"], "ok")
            self.assertTrue(str(artifact["proof_ref"]).endswith("public-proof/BATCH-01.json"))
            persisted = json.loads((orch / "public-proof" / "BATCH-01.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "ok")
            self.assertEqual(persisted["contract"]["value_target"], "portfolio_first_brief")
            self.assertIn("http://3.98.20.77/api/health", persisted["public_urls_checked"])


if __name__ == "__main__":
    unittest.main()
