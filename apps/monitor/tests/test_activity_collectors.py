from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.monitor.src.collectors import collect_activity_events


class ActivityCollectorsTests(unittest.TestCase):
    def test_collect_activity_events_normalizes_actions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            orch = root / "docs" / "operations" / "orchestrator"
            state = root / "state"
            runner = root / "logs-codex-runs" / "role-runner"
            runner.mkdir(parents=True, exist_ok=True)
            orch.mkdir(parents=True, exist_ok=True)
            state.mkdir(parents=True, exist_ok=True)

            (orch / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "at": "2026-03-06T11:00:00Z",
                                "kind": "claim",
                                "details": {"role": "dev", "task_id": "BATCH-27-DEV-01"},
                            }
                        ),
                        json.dumps(
                            {
                                "at": "2026-03-06T11:05:00Z",
                                "kind": "complete",
                                "details": {
                                    "role": "dev",
                                    "task_id": "BATCH-27-DEV-01",
                                    "artifact": "apps/api/src/foo.py",
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            (runner / "dev.events.log").write_text(
                "\n".join(
                    [
                        "2026-03-06T11:06:00Z role=dev event=primary_prompt_end detail=tick=P1 rc=0",
                        "2026-03-06T11:07:00Z role=dev event=final_output detail=tick=P1",
                    ]
                ),
                encoding="utf-8",
            )

            payload = collect_activity_events(root=root, state_dir=state, window_hours=6, limit=200)
            self.assertGreaterEqual(payload["count"], 2)
            actions = {row["action"] for row in payload["timeline"]}
            self.assertIn("CLAIM", actions)
            self.assertIn("COMPLETE", actions)
            self.assertTrue(all(row.get("event_id") for row in payload["timeline"]))


if __name__ == "__main__":
    unittest.main()
