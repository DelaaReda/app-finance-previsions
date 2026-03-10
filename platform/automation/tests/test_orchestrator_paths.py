from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from orchestrator_paths import (
    load_runtime_state,
    persist_runtime_state,
    resolve_orchestrator_read_path,
    runtime_state_is_paused,
    runtime_state_root,
)


class OrchestratorPathsTests(unittest.TestCase):
    def test_prefers_runtime_state_over_docs_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runtime_root = runtime_state_root(root)
            docs_root = root / "docs" / "operations" / "orchestrator"
            runtime_root.mkdir(parents=True, exist_ok=True)
            docs_root.mkdir(parents=True, exist_ok=True)
            (docs_root / "priority-queue.json").write_text(json.dumps({"items": [{"id": "OLD"}]}), encoding="utf-8")
            (runtime_root / "priority-queue.json").write_text(json.dumps({"items": [{"id": "NEW"}]}), encoding="utf-8")

            resolved = resolve_orchestrator_read_path(root, "priority-queue.json")

            self.assertEqual(resolved, runtime_root / "priority-queue.json")

    def test_falls_back_to_docs_when_runtime_state_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_root = root / "docs" / "operations" / "orchestrator"
            docs_root.mkdir(parents=True, exist_ok=True)
            (docs_root / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")

            resolved = resolve_orchestrator_read_path(root, "parallel-workstreams.json")

            self.assertEqual(resolved, docs_root / "parallel-workstreams.json")

    def test_runtime_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            persist_runtime_state(
                root,
                lifecycle="paused",
                reason="operator_paused_runtime",
                execution_mode="planner_experimental",
                operator_mode="paused",
                source="unit_test",
            )

            state = load_runtime_state(root)

            self.assertEqual(state.get("lifecycle"), "paused")
            self.assertEqual(state.get("reason"), "operator_paused_runtime")
            self.assertEqual(state.get("execution_mode"), "planner_experimental")

    def test_runtime_state_is_paused_true_for_maintenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            persist_runtime_state(
                root,
                lifecycle="maintenance",
                reason="operator_maintenance_runtime",
                execution_mode="planner_experimental",
                operator_mode="paused",
                source="unit_test",
            )

            self.assertTrue(runtime_state_is_paused(root))


if __name__ == "__main__":
    unittest.main()
