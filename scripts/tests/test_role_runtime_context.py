#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "role_runtime_context.py"


class RoleRuntimeContextTests(unittest.TestCase):
    def test_builds_context_with_queue_and_directives(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "docs/orchestrator-ops").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/planning").mkdir(parents=True, exist_ok=True)
            (workspace / "state").mkdir(parents=True, exist_ok=True)
            (workspace / "memory/agents").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/ops").mkdir(parents=True, exist_ok=True)
            (workspace / "logs").mkdir(parents=True, exist_ok=True)

            queue = {
                "items": [
                    {
                        "id": "BATCH-02",
                        "title": "Implement status propagation",
                        "state": "READY",
                        "next_action": "DISPATCH_BATCH02",
                    },
                    {
                        "id": "BATCH-01",
                        "title": "Previous gate",
                        "state": "BLOCKED",
                        "blocker_id": "NEEDS_QA",
                    },
                ]
            }
            (workspace / "docs/orchestrator-ops/priority-queue.json").write_text(
                json.dumps(queue), encoding="utf-8"
            )
            (workspace / "docs/planning/WORKSTATE.md").write_text(
                "Working on orchestration status and channel impacts.\n", encoding="utf-8"
            )
            (workspace / "state/dev.last_contract").write_text(
                "STATUS: IN_PROGRESS\nDELTA: DEV_TICK\nNEXT_ACTION_UNIQUE: DEV_ACTION\n", encoding="utf-8"
            )
            (workspace / "state/qa.last_contract").write_text(
                "STATUS: IN_PROGRESS\nDELTA: QA_TICK\nNEXT_ACTION_UNIQUE: QA_ACTION\n", encoding="utf-8"
            )
            (workspace / "memory/agents/dev.md").write_text("# dev\n- recent note\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_CHAT.md").write_text("chat line\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md").write_text("iter line\n", encoding="utf-8")
            (workspace / "logs/dev.live.log").write_text("trace line\n", encoding="utf-8")
            (workspace / "docs/ops/DIRECTIVE_BUS.jsonl").write_text(
                json.dumps(
                    {
                        "id": "DIR-001",
                        "kind": "policy",
                        "msg": "prioritize batch02",
                        "targets": ["dev"],
                        "ts": "2026-02-27T10:00:00Z",
                        "expires_at": "2026-12-31T00:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "dev",
                    str(workspace),
                    str(workspace / "state"),
                    str(workspace / "memory/agents"),
                    str(workspace / "docs/ops/ADMIN_TEAM_CHAT.md"),
                    str(workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md"),
                    str(workspace / "docs/ops/DIRECTIVE_BUS.jsonl"),
                    str(workspace / "logs/dev.live.log"),
                    str(workspace / "state/dev.last_contract"),
                    "queue_v_test",
                    "workboard_v_test",
                    "1",
                    "0",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            out = cp.stdout.strip()
            self.assertIn("RUNTIME_CONTEXT:", out)
            self.assertIn("queue_has_ready=1", out)
            self.assertIn("ready_items=BATCH-02:Implement status propagation", out)
            self.assertIn("blocked_items=BATCH-01:NEEDS_QA", out)
            self.assertIn("self_last_contract=self:status=IN_PROGRESS", out)
            self.assertIn("peer_contracts=qa:status=IN_PROGRESS", out)
            self.assertIn("directives_tail=DIR-001:policy:prioritize batch02", out)


if __name__ == "__main__":
    unittest.main()
