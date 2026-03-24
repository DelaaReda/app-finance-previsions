from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from orchestrator_paths import resolve_orchestrator_read_path
from planning.plane.plane_runtime_sync import ingest_plane_payload, main, reconcile_from_plane_api
from runtime.truth.event_store import EventStore


class PlaneRuntimeSyncTests(unittest.TestCase):
    def test_snapshot_payload_updates_runtime_and_projections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "workspace_slug": "finance",
                "project_id": "proj-1",
                "project_slug": "finance-copilot",
                "modules": [
                    {
                        "id": "module-1",
                        "identifier": "BATCH-01",
                        "name": "BATCH-01",
                        "state": "planned",
                    }
                ],
                "work_items": [
                    {
                        "id": "wi-1",
                        "module_id": "module-1",
                        "identifier": "BATCH-01-DEV-01",
                        "name": "BATCH-01-DEV-01",
                        "state": "planned",
                    }
                ],
            }

            result = ingest_plane_payload(root, payload)

            self.assertTrue(result["accepted"])
            self.assertEqual(result["source"], "snapshot")
            self.assertEqual(result["apply_result"]["runtime_result"]["sync_source"], "snapshot")
            self.assertEqual(result["apply_result"]["runtime_result"]["graph_states_upserted"], 1)
            queue_path = resolve_orchestrator_read_path(root, "priority-queue.json")
            workboard_path = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
            self.assertTrue(queue_path.exists())
            self.assertTrue(workboard_path.exists())
            latest = EventStore(root).latest_graph_states(limit=1)
            self.assertEqual(latest[0]["capability_request"]["planning_source"], "plane")
            self.assertEqual(latest[0]["capability_request"]["plane_work_item_id"], "wi-1")

    def test_webhook_event_validates_signature_and_updates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module_payload = {
                "event": "module",
                "action": "create",
                "data": {
                    "id": "module-1",
                    "identifier": "BATCH-01",
                    "name": "BATCH-01",
                    "state": "planned",
                },
            }
            item_payload = {
                "event": "issue",
                "action": "create",
                "data": {
                    "id": "wi-1",
                    "module_id": "module-1",
                    "identifier": "BATCH-01-DEV-01",
                    "name": "BATCH-01-DEV-01",
                    "state": "planned",
                },
            }

            with patch.dict(os.environ, {"FC_PLANE_WEBHOOK_SECRET": "secret-token"}, clear=False):
                module_raw = json.dumps(module_payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
                module_sig = hmac.new(b"secret-token", msg=module_raw, digestmod=hashlib.sha256).hexdigest()
                module_result = ingest_plane_payload(
                    root,
                    module_payload,
                    raw_body=module_raw,
                    headers={"X-Plane-Signature": module_sig, "X-Plane-Event": "module"},
                )
                item_raw = json.dumps(item_payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
                item_sig = hmac.new(b"secret-token", msg=item_raw, digestmod=hashlib.sha256).hexdigest()
                item_result = ingest_plane_payload(
                    root,
                    item_payload,
                    raw_body=item_raw,
                    headers={"X-Plane-Signature": item_sig, "X-Plane-Event": "issue"},
                )

            self.assertTrue(module_result["accepted"])
            self.assertEqual(module_result["signature"], "verified")
            self.assertTrue(item_result["accepted"])
            self.assertEqual(item_result["apply_result"]["runtime_result"]["sync_source"], "webhook")
            self.assertEqual(item_result["work_items"], 1)
            cache_path = resolve_orchestrator_read_path(root, "plane-sync-snapshot.json")
            self.assertTrue(cache_path.exists())

    def test_reconcile_from_plane_api_fetches_modules_and_work_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modules_payload = [
                {
                    "id": "module-1",
                    "identifier": "BATCH-01",
                    "name": "BATCH-01",
                    "state": "planned",
                }
            ]
            module_items_payload = [
                {
                    "id": "wi-1",
                    "module_id": "module-1",
                    "identifier": "BATCH-01-DEV-01",
                    "name": "BATCH-01-DEV-01",
                    "state": "planned",
                }
            ]

            with patch.dict(
                os.environ,
                {
                    "FC_PLANE_BASE_URL": "https://plane.example.test",
                    "FC_PLANE_API_KEY": "plane-key",
                    "FC_PLANE_WORKSPACE_SLUG": "finance",
                    "FC_PLANE_PROJECT_ID": "proj-1",
                    "FC_PLANE_PROJECT_SLUG": "finance-copilot",
                },
                clear=False,
            ):
                with patch(
                    "planning.plane.plane_runtime_sync._plane_get_json",
                    side_effect=[modules_payload, module_items_payload],
                ):
                    result = reconcile_from_plane_api(root)

            self.assertTrue(result["accepted"])
            self.assertEqual(result["source"], "reconcile_api")
            self.assertEqual(result["apply_result"]["runtime_result"]["sync_source"], "reconcile_api")
            self.assertEqual(result["modules"], 1)
            self.assertEqual(result["work_items"], 1)
            latest = EventStore(root).latest_graph_states(limit=1)
            self.assertEqual(latest[0]["capability_request"]["plane_module_id"], "module-1")

    def test_cli_apply_routes_through_ingest_plane_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modules_path = root / "modules.json"
            work_items_path = root / "work-items.json"
            modules_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "module-1",
                            "identifier": "BATCH-01",
                            "name": "BATCH-01",
                            "state": "planned",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            work_items_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "wi-1",
                            "module_id": "module-1",
                            "identifier": "BATCH-01-DEV-01",
                            "name": "BATCH-01-DEV-01",
                            "state": "planned",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with patch("planning.plane.plane_runtime_sync.ingest_plane_payload") as ingest_mock:
                ingest_mock.return_value = {
                    "accepted": True,
                    "source": "snapshot",
                    "apply_result": {"runtime_result": {"sync_source": "snapshot"}},
                }
                rc = main(
                    [
                        "--root",
                        str(root),
                        "--modules-file",
                        str(modules_path),
                        "--work-items-file",
                        str(work_items_path),
                        "--workspace-slug",
                        "finance",
                        "--project-id",
                        "proj-1",
                        "--project-slug",
                        "finance-copilot",
                        "--apply",
                    ]
                )

            self.assertEqual(rc, 0)
            ingest_mock.assert_called_once()
            payload = ingest_mock.call_args.args[1]
            self.assertEqual(payload["sync_source"], "snapshot")
            self.assertEqual(payload["workspace_slug"], "finance")
            self.assertEqual(payload["project_id"], "proj-1")
            self.assertEqual(len(payload["modules"]), 1)
            self.assertEqual(len(payload["work_items"]), 1)
