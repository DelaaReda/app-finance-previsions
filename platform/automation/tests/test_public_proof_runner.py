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

    def test_api_wave_public_proof_persists_endpoint_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            manifest_dir = root / "platform" / "automation" / "config"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "api_wave_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "api_wave_manifest.v1",
                        "mode": "api_autonomy_mode",
                        "enabled": True,
                        "wave_batch_id": "API-WAVE",
                        "stream_id": "API-WAVE",
                        "items": [
                            {
                                "endpoint_id": "copilot-search",
                                "domain": "copilot",
                                "route_path": "/api/search/tickers",
                                "route_module": "apps/api/src/domains/copilot/api/search.py",
                                "priority": "P1",
                                "product_surface": "copilot",
                                "shared_contract": "packages/contracts/copilot_v1.py",
                                "endpoint_service": "apps/api/src/domains/copilot/application/copilot_search_endpoint_service.py",
                                "public_smoke_path": "/api/search/tickers?q=NVDA",
                                "canonical": True,
                                "alias_only": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (orch / "runtime-state.json").write_text(
                json.dumps({"lifecycle": "running", "execution_mode": "api_autonomy_mode"}),
                encoding="utf-8",
            )
            (orch / "api_wave_state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "api_wave_state.v1",
                        "wave_batch_id": "API-WAVE",
                        "stream_id": "API-WAVE",
                        "mode": "api_autonomy_mode",
                        "current_endpoint_id": "copilot-search",
                        "current_task_id": "APIWAVE-COPILOT_SEARCH-DEV-01",
                        "current_owner_task_id": "APIWAVE-COPILOT_SEARCH-DEV-01",
                        "current_status": "verifying_public_proof",
                        "completed_endpoint_ids": [],
                        "deferred_endpoint_ids": [],
                    }
                ),
                encoding="utf-8",
            )
            persist_product_delivery_state(
                root,
                {
                    "schema_version": "product_delivery_state.v1",
                    "active_batch_id": "API-WAVE",
                    "phase": "verifying_public_proof",
                    "product_done": False,
                    "ops_clean": False,
                    "public_proof_status": "degraded",
                    "user_visible_delta_confirmed": False,
                    "next_batch_eligible": False,
                    "ec2_reachable": True,
                    "freeze_reason": "waiting_public_proof",
                    "api_autonomy_mode": True,
                    "api_wave": {"current_endpoint_id": "copilot-search"},
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
                "runtime.truth.public_proof_runner._fetch_json_payload",
                return_value={
                    "ok": True,
                    "data": {"matches": [{"ticker": "NVDA"}]},
                    "source": "cache",
                    "freshness": {"age_s": 12},
                    "warnings": [],
                    "stats": {"count": 1},
                },
            ), mock.patch(
                "runtime.truth.public_proof_runner.run_browser_smoke",
                side_effect=AssertionError("ui smoke should stay optional for api wave"),
            ):
                artifact = run_public_proof(root)

            self.assertEqual(artifact["endpoint_id"], "copilot-search")
            self.assertEqual(artifact["route_path"], "/api/search/tickers")
            self.assertEqual(artifact["status"], "ok")
            self.assertEqual(artifact["ui_smoke_status"], "skipped")
            self.assertTrue(str(artifact["proof_ref"]).endswith("api-wave-proofs/copilot_search.json"))
            persisted_path = orch / "api-wave-proofs" / "copilot_search.json"
            persisted = json.loads(persisted_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["contract_status"], "ok")
            self.assertEqual(persisted["metadata_status"], "ok")
            self.assertEqual(persisted["fallback_status"], "ok")


if __name__ == "__main__":
    unittest.main()
