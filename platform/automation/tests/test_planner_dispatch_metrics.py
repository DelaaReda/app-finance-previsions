from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "planner_dispatch_metrics.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_dispatch_metrics", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_dispatch_metrics"] = MODULE
SPEC.loader.exec_module(MODULE)


build_planner_dispatch_metrics = MODULE.build_planner_dispatch_metrics


class PlannerDispatchMetricsTests(unittest.TestCase):
    def test_build_planner_dispatch_metrics_counts_success_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            results = orch / "planner-subagents-results"
            results.mkdir(parents=True, exist_ok=True)
            registry = {
                "subagents": [
                    {
                        "subagent_id": "planner_dev_ok",
                        "target_role": "dev",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-1-DEV-01",
                        "status": "completed",
                        "summary": "ok",
                        "artifact": "artifact.txt",
                        "last_update_at": "2026-03-07T06:00:00Z",
                    },
                    {
                        "subagent_id": "planner_admin_fail",
                        "target_role": "admin",
                        "parent_role": "planner",
                        "owner_task_id": "BATCH-2-ADMIN-01",
                        "status": "failed",
                        "summary": "failed",
                        "artifact": "artifact.txt",
                        "last_update_at": "2026-03-07T06:01:00Z",
                    },
                ]
            }
            (orch / "planner-subagents-registry.json").write_text(json.dumps(registry), encoding="utf-8")
            (results / "planner_dev_ok.raw.txt").write_text("normal success", encoding="utf-8")
            (results / "planner_admin_fail.raw.txt").write_text("Gateway agent failed; falling back to embedded", encoding="utf-8")

            metrics = build_planner_dispatch_metrics(root, recent_limit=12)

            self.assertEqual(metrics["recent_total"], 2)
            self.assertEqual(metrics["recent_success_count"], 1)
            self.assertEqual(metrics["recent_failed_count"], 1)
            self.assertEqual(metrics["recent_fallback_like_count"], 1)
            self.assertEqual(metrics["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
