from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

if "yaml" not in sys.modules:
    fake_yaml = types.ModuleType("yaml")
    fake_yaml.safe_load = lambda *args, **kwargs: {}
    fake_yaml.safe_dump = lambda *args, **kwargs: ""
    sys.modules["yaml"] = fake_yaml

MODULE_PATH = AUTOMATION_DIR / "runtime" / "planner" / "planner_runtime_actions.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_runtime_actions", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_runtime_actions"] = MODULE
SPEC.loader.exec_module(MODULE)


class PlannerRuntimeActionsCollectTests(unittest.TestCase):
    def test_collect_finished_admin_subagents_skips_done_owner_without_collecting(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "logs-codex-runs" / "orchestrator-state"
            orch.mkdir(parents=True, exist_ok=True)
            legacy = orch / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-84"]},
                        "tasks": [
                            {
                                "id": "BATCH-84-ADMIN-01",
                                "stream_id": "BATCH-84",
                                "role": "admin",
                                "state": "DONE",
                                "completed_at": "2026-04-15T00:00:00Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (legacy / "planner-subagents-registry.json").write_text(
                json.dumps(
                    {
                        "subagents": [
                            {
                                "subagent_id": "planner_admin_done",
                                "parent_role": "planner",
                                "target_role": "admin",
                                "owner_task_id": "BATCH-84-ADMIN-01",
                                "status": "running",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            results_dir = legacy / "planner-subagents-results"
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "planner_admin_done.raw.txt").write_text("stale compat payload", encoding="utf-8")

            with mock.patch.object(MODULE, "collect_subagent", side_effect=AssertionError("collect_subagent should not run")):
                actions = MODULE._collect_finished_admin_subagents(root, source="unit_test")

            self.assertIn("admin_skip_done:BATCH-84-ADMIN-01", actions)
            registry = json.loads((legacy / "planner-subagents-registry.json").read_text(encoding="utf-8"))
            self.assertEqual(registry.get("subagents"), [])


if __name__ == "__main__":
    unittest.main()
