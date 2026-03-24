from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_ROOT = ROOT / "platform" / "automation"
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))

from runtime.model_plane import CodexCliAdapter
from runtime.model_plane import (
    CollectInvocationRequest,
    StartInvocationRequest,
    StatusInvocationRequest,
)


class ModelPlaneAdapterTests(unittest.TestCase):
    def test_adapter_autofills_stable_invocation_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            adapter = CodexCliAdapter(Path(td))

            started = adapter.start(
                StartInvocationRequest(
                    cycle_id="cycle-1",
                    batch_id="BATCH-100",
                    task_id="BATCH-100-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    backend="codex_exec",
                    session_id="session-1",
                    prompt_digest="abc123",
                )
            )
            self.assertTrue(started["invocation_id"])
            self.assertTrue(started["idempotency_key"])
            self.assertTrue(started["heartbeat_ts"])
            self.assertEqual(started["invocation_status"], "started")
            self.assertEqual(started["provider_plane"], "agent")
            self.assertEqual(started["policy_plane"], "model_plane")
            self.assertEqual(started["fallback_reason"], "none")
            self.assertEqual(started["backend_requested"], "codex_exec")
            self.assertEqual(started["backend_used"], "codex_exec")

            status = adapter.status(
                StatusInvocationRequest(
                    cycle_id="cycle-1",
                    batch_id="BATCH-100",
                    task_id="BATCH-100-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    backend="codex_exec",
                    session_id="session-1",
                    invocation_id=started["invocation_id"],
                    idempotency_key=started["idempotency_key"],
                    invocation_status="running",
                )
            )
            self.assertEqual(status["invocation_id"], started["invocation_id"])
            self.assertEqual(status["idempotency_key"], started["idempotency_key"])
            self.assertEqual(status["invocation_status"], "running")
            self.assertTrue(status["heartbeat_ts"])
            self.assertEqual(status["backend_requested"], "codex_exec")
            self.assertEqual(status["backend_used"], "codex_exec")
            self.assertEqual(status["policy_plane"], "model_plane")

            collected = adapter.collect(
                CollectInvocationRequest(
                    cycle_id="cycle-1",
                    batch_id="BATCH-100",
                    task_id="BATCH-100-DEV-01",
                    owner_role="planner",
                    target_role="dev",
                    backend="codex_exec",
                    session_id="session-1",
                    invocation_id=started["invocation_id"],
                    idempotency_key=started["idempotency_key"],
                    result_status="pass",
                    rc=0,
                    result_ref="logs/result.json",
                ),
                {"status": "pass"},
            )
            self.assertEqual(collected["invocation_id"], started["invocation_id"])
            self.assertEqual(collected["idempotency_key"], started["idempotency_key"])
            self.assertEqual(collected["invocation_status"], "pass")
            self.assertTrue(collected["heartbeat_ts"])
            self.assertEqual(collected["provider_plane"], "agent")
            self.assertEqual(collected["policy_plane"], "model_plane")
            self.assertEqual(collected["fallback_reason"], "none")


if __name__ == "__main__":
    unittest.main()
