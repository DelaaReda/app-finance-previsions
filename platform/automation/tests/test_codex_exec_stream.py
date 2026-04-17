from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "codex_exec_stream.py"
SPEC = importlib.util.spec_from_file_location("fc_codex_exec_stream", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_codex_exec_stream"] = MODULE
SPEC.loader.exec_module(MODULE)


class CodexExecStreamTests(unittest.TestCase):
    def test_extracts_thread_and_message_from_concatenated_event_stream(self) -> None:
        payload = (
            '{"type":"thread.started","thread_id":"019d9630-86b2"} '
            '{"type":"turn.started"} '
            '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"STATUS: IN_PROGRESS\\n'
            'DELTA: PLANNER_DISPATCH_ACTIVE\\n'
            'EVIDENCE: task_update=handoff; lock_check=ok\\n'
            'RISKS: none\\n'
            'NEXT: owner=dev; action=continue\\n'
            'VERDICT: GO_WITH_CAUTION\\n'
            'BLOCKER_ID: NONE\\n'
            'NEXT_ACTION_UNIQUE: NEXT_PLANNER_TEST_123"}}'
        )

        self.assertEqual(MODULE.extract_thread_id(payload), "019d9630-86b2")
        message = MODULE.extract_message(payload)
        self.assertIn("STATUS: IN_PROGRESS", message)
        self.assertIn("NEXT_ACTION_UNIQUE: NEXT_PLANNER_TEST_123", message)

    def test_extracts_message_from_nested_content_shape(self) -> None:
        payload = (
            '\x1b[32m{"type":"message.completed","message":{"type":"message","content":['
            '{"type":"output_text","text":"STATUS: PASS\\n'
            'DELTA: NO_DELTA\\n'
            'EVIDENCE: task_update=done; lock_check=ok\\n'
            'RISKS: none\\n'
            'NEXT: owner=none; action=none\\n'
            'VERDICT: PASS\\n'
            'BLOCKER_ID: NONE\\n'
            'NEXT_ACTION_UNIQUE: TEST_DONE_456"}]}}\x1b[0m'
        )

        message = MODULE.extract_message(payload)
        self.assertIn("STATUS: PASS", message)
        self.assertIn("NEXT_ACTION_UNIQUE: TEST_DONE_456", message)


if __name__ == "__main__":
    unittest.main()
