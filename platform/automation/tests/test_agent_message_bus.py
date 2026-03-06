#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "platform" / "automation" / "agent_message_bus.py"
MSG_ID_RE = re.compile(r"^MSG_[0-9]{8}T[0-9]{6}Z_[0-9A-HJKMNP-TV-Z]{26}$")


def run_bus(*args: str, bus_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--bus-file", str(bus_file), *args],
        text=True,
        capture_output=True,
        check=False,
    )


class AgentMessageBusTests(unittest.TestCase):
    def test_post_records_auto_post_metadata_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bus_file = Path(td) / "AGENT_MESSAGE_BUS.jsonl"
            post = run_bus(
                "post",
                "--targets",
                "planner",
                "--msg",
                "sync queue/workboard now",
                "--id",
                "MSG_SM_20260306T000000Z_ABCD1234",
                "--auto-post-reason",
                "queue_workboard_desync",
                "--auto-generated-id",
                "1",
                bus_file=bus_file,
            )
            self.assertEqual(post.returncode, 0, msg=post.stderr)
            rows = [json.loads(line) for line in bus_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.get("event"), "message_posted")
            self.assertEqual(row.get("auto_post_reason"), "queue_workboard_desync")
            self.assertTrue(bool(row.get("auto_generated_id")))

    def test_post_deliver_action_close_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bus_file = Path(td) / "AGENT_MESSAGE_BUS.jsonl"
            post = run_bus("post", "--targets", "dev", "--msg", "apply hotfix", bus_file=bus_file)
            self.assertEqual(post.returncode, 0, msg=post.stderr)
            out = post.stdout.strip()
            self.assertIn("message_id=", out)
            message_id = out.split("message_id=", 1)[1].split(" ", 1)[0].strip()
            self.assertRegex(message_id, MSG_ID_RE)

            active_before = run_bus("active", "--role", "dev", "--json", bus_file=bus_file)
            self.assertEqual(active_before.returncode, 0, msg=active_before.stderr)
            rows = json.loads(active_before.stdout)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["message_id"], message_id)

            deliver = run_bus("deliver", "--id", message_id, "--role", "dev", "--tick", "TICK-1", bus_file=bus_file)
            self.assertEqual(deliver.returncode, 0, msg=deliver.stderr)

            dedupe = run_bus("deliver", "--id", message_id, "--role", "dev", "--tick", "TICK-1", bus_file=bus_file)
            self.assertEqual(dedupe.returncode, 0, msg=dedupe.stderr)
            self.assertIn("NOOP", dedupe.stdout)

            action = run_bus(
                "action",
                "--id",
                message_id,
                "--role",
                "dev",
                "--status",
                "done",
                "--note",
                "applied and verified",
                "--tick",
                "TICK-1",
                bus_file=bus_file,
            )
            self.assertEqual(action.returncode, 0, msg=action.stderr)

            close = run_bus("close", "--id", message_id, "--reason", "resolved", bus_file=bus_file)
            self.assertEqual(close.returncode, 0, msg=close.stderr)

            action_after_close = run_bus(
                "action",
                "--id",
                message_id,
                "--role",
                "dev",
                "--status",
                "done",
                "--note",
                "late update",
                "--tick",
                "TICK-2",
                bus_file=bus_file,
            )
            self.assertNotEqual(action_after_close.returncode, 0)
            self.assertIn("closed", action_after_close.stderr.lower())

            active_after = run_bus("active", "--role", "dev", "--json", bus_file=bus_file)
            self.assertEqual(active_after.returncode, 0, msg=active_after.stderr)
            self.assertEqual(json.loads(active_after.stdout), [])

            history = run_bus("history", "--id", message_id, bus_file=bus_file)
            self.assertEqual(history.returncode, 0, msg=history.stderr)
            events = json.loads(history.stdout)
            kinds = [row.get("event") for row in events]
            self.assertIn("message_posted", kinds)
            self.assertIn("message_delivered", kinds)
            self.assertIn("message_action", kinds)
            self.assertIn("message_closed", kinds)

    def test_collision_and_expired_message_not_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bus_file = Path(td) / "AGENT_MESSAGE_BUS.jsonl"
            fixed_id = "MSG_20260304T120000Z_01ARZ3NDEKTSV4RRFFQ69G5FAV"
            first = run_bus(
                "post",
                "--targets",
                "planner",
                "--msg",
                "priority sync",
                "--id",
                fixed_id,
                bus_file=bus_file,
            )
            self.assertEqual(first.returncode, 0, msg=first.stderr)

            second = run_bus(
                "post",
                "--targets",
                "planner",
                "--msg",
                "duplicate",
                "--id",
                fixed_id,
                bus_file=bus_file,
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("collision", second.stderr.lower())

            expired_id = "MSG_20260304T120001Z_01ARZ3NDEKTSV4RRFFQ69G5FB0"
            expired_record = {
                "event": "message_posted",
                "message_id": expired_id,
                "ts_utc": "2026-03-01T00:00:00Z",
                "source": "main",
                "targets": ["planner"],
                "priority": "normal",
                "sticky": True,
                "ttl_min": 1,
                "expires_at_utc": "2026-03-01T00:01:00Z",
                "payload": "stale",
                "role": "",
                "tick_id": "",
                "action_status": "",
                "note": "",
                "close_reason": "",
            }
            with bus_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(expired_record) + "\n")

            active = run_bus("active", "--role", "planner", "--json", bus_file=bus_file)
            self.assertEqual(active.returncode, 0, msg=active.stderr)
            rows = json.loads(active.stdout)
            ids = {row.get("message_id") for row in rows}
            self.assertIn(fixed_id, ids)
            self.assertNotIn(expired_id, ids)

            deliver_expired = run_bus(
                "deliver",
                "--id",
                expired_id,
                "--role",
                "planner",
                "--tick",
                "TICK-EXP",
                bus_file=bus_file,
            )
            self.assertNotEqual(deliver_expired.returncode, 0)
            self.assertIn("expired", deliver_expired.stderr.lower())

    def test_deliver_dedup_is_scoped_per_role(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bus_file = Path(td) / "AGENT_MESSAGE_BUS.jsonl"
            post = run_bus(
                "post",
                "--targets",
                "all",
                "--msg",
                "orchestrate sync",
                "--id",
                "MSG_20260304T120222Z_01ARZ3NDEKTSV4RRFFQ69G5FC1",
                bus_file=bus_file,
            )
            self.assertEqual(post.returncode, 0, msg=post.stderr)
            message_id = "MSG_20260304T120222Z_01ARZ3NDEKTSV4RRFFQ69G5FC1"

            deliver_dev = run_bus("deliver", "--id", message_id, "--role", "dev", "--tick", "TD1", bus_file=bus_file)
            self.assertEqual(deliver_dev.returncode, 0, msg=deliver_dev.stderr)

            deliver_planner = run_bus(
                "deliver", "--id", message_id, "--role", "planner", "--tick", "TP1", bus_file=bus_file
            )
            self.assertEqual(deliver_planner.returncode, 0, msg=deliver_planner.stderr)

            deliver_dev_dup = run_bus(
                "deliver", "--id", message_id, "--role", "dev", "--tick", "TD2", bus_file=bus_file
            )
            self.assertEqual(deliver_dev_dup.returncode, 0, msg=deliver_dev_dup.stderr)
            self.assertIn("NOOP", deliver_dev_dup.stdout)


if __name__ == "__main__":
    unittest.main()
