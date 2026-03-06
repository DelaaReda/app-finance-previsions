#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUS_SH = ROOT / "platform" / "automation" / "agent_message_bus.sh"
RUNNER = ROOT / "platform" / "automation" / "cron_tmux_role_runner.sh"


class MessageBusAutoIdTests(unittest.TestCase):
    def test_post_without_id_generates_message_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bus_file = Path(td) / "AGENT_MESSAGE_BUS.jsonl"
            env = os.environ.copy()
            env["AGENT_MESSAGE_BUS_FILE"] = str(bus_file)
            cp = subprocess.run(
                [
                    "bash",
                    str(BUS_SH),
                    "post",
                    "--targets",
                    "dev",
                    "--msg",
                    "corriger contrat et claim maintenant",
                    "--priority",
                    "high",
                    "--sticky",
                    "1",
                    "--ttl-min",
                    "120",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertRegex(cp.stdout, r"message_id=MSG[_A-Za-z0-9-]+")
            rows = [json.loads(line) for line in bus_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].get("event"), "message_posted")
            message_id = str(rows[0].get("message_id", ""))
            self.assertTrue(message_id.startswith("MSG"))
            self.assertTrue(re.fullmatch(r"MSG[-_A-Za-z0-9]{3,120}", message_id))

    def test_runner_contains_auto_id_emit_trace(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("agent_msg_emit_autoid", text)
        self.assertIn("agent_msg_emit_dedup_skip", text)
        self.assertIn("scrum_action_posted", text)
        self.assertIn("scrum_action_skipped_cooldown", text)
        self.assertIn("scrum_action_skipped_dedup", text)


if __name__ == "__main__":
    unittest.main()
