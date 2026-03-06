#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "platform" / "automation" / "cron_tmux_role_runner.sh"


class RunnerMessageReceiptsTests(unittest.TestCase):
    def test_runner_contains_delivery_dedupe_and_action_receipts(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("record_agent_message_receipts()", text)
        self.assertIn("AGENT_MESSAGE_BUS_SCRIPT\" deliver --id", text)
        self.assertIn("reason=already_delivered_or_missing", text)
        self.assertIn("extract_message_bus_intents_from_evidence", text)
        self.assertIn("message_to_<planner|dev|admin>", text)
        self.assertIn("AGENT_MESSAGE_BUS_SCRIPT\" action --id", text)
        self.assertIn("message_ack", text)
        self.assertIn("message_id", text)

    def test_runner_records_receipts_on_primary_retry_and_fallback(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('record_agent_message_receipts "$STRUCTURED" "$PRIMARY_TICK"', text)
        self.assertIn('record_agent_message_receipts "$STRUCTURED" "$RETRY_TICK"', text)
        self.assertIn('record_agent_message_receipts "$STRUCTURED" "$CODEX_TICK"', text)
        self.assertIn('record_agent_message_receipts "$FALLBACK_OUTPUT" "$FALLBACK_TICK"', text)


    def test_runner_soft_skips_invalid_intents_without_fatal_errors(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("agent_msg_intent_skip", text)
        self.assertIn("scrum_auto_intents_error", text)
        self.assertIn("agent_msg_emit_skip", text)
        self.assertIn("return 0", text)


if __name__ == "__main__":
    unittest.main()
