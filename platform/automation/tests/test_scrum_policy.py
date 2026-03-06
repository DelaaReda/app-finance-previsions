from __future__ import annotations

import json
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "scrum_policy.py"
SPEC = importlib.util.spec_from_file_location("fc_scrum_policy", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_scrum_policy"] = MODULE
SPEC.loader.exec_module(MODULE)
PolicyConfig = MODULE.PolicyConfig
evaluate_policy = MODULE.evaluate_policy


class ScrumPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        self.queue_path = orch / "priority-queue.json"
        self.board_path = orch / "parallel-workstreams.json"
        self.report_path = orch / "state-reconcile-report.json"
        self.state_dir = self.root / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.policy_state = self.state_dir / "scrum_policy_state.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _config(self) -> PolicyConfig:
        return PolicyConfig(
            root=self.root,
            state_dir=self.state_dir,
            queue_path=self.queue_path,
            board_path=self.board_path,
            reconcile_report_path=self.report_path,
            state_file=self.policy_state,
            ready_starvation_seconds=300,
            stalled_in_progress_seconds=300,
            escalate_after_cycles=2,
        )

    def test_ready_starvation_triggers_message(self) -> None:
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        self.report_path.write_text(json.dumps({}), encoding="utf-8")
        self.board_path.write_text(json.dumps({"tasks": [{"id": "BATCH-27-DEV-01", "role": "dev", "state": "READY_DEV", "updated_at": "2026-03-06T00:00:00Z", "ready_starvation": True}]}), encoding="utf-8")
        result = evaluate_policy(self._config(), now_epoch=1772800000)
        self.assertTrue(any(intent.target == "dev" and intent.reason == "ready_starvation" for intent in result.intents))

    def test_guard_block_triggers_targeted_message(self) -> None:
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        self.report_path.write_text(json.dumps({}), encoding="utf-8")
        self.board_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
        (self.state_dir / "dev.last_contract").write_text("\n".join([
            "STATUS: BLOCKED",
            "DELTA: CONTRACT_GUARD_BLOCK",
            "EVIDENCE: task_update=blocked; lock_check=ok; run_note=blocked by guard; issues=contract_guard_dev_arch_check_format_invalid; issue_count=1; issue_severity=high",
            "RISKS: invalid arch check",
            "NEXT: owner=dev; action=fix",
            "VERDICT: BLOCKED",
            "BLOCKER_ID: DEV_ARCH_CHECK_FORMAT_INVALID",
            "NEXT_ACTION_UNIQUE: DEV_FIX",
        ]), encoding="utf-8")
        result = evaluate_policy(self._config(), now_epoch=1772800000)
        self.assertTrue(any(intent.target == "dev" and intent.reason == "contract_guard_block" for intent in result.intents))

    def test_persisted_block_escalates_to_admin(self) -> None:
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        self.report_path.write_text(json.dumps({}), encoding="utf-8")
        self.board_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
        contract = "\n".join([
            "STATUS: BLOCKED",
            "DELTA: CONTRACT_GUARD_BLOCK",
            "EVIDENCE: task_update=blocked; lock_check=ok; run_note=blocked by guard; issues=contract_guard_dev_arch_check_format_invalid; issue_count=1; issue_severity=high",
            "RISKS: invalid arch check",
            "NEXT: owner=dev; action=fix",
            "VERDICT: BLOCKED",
            "BLOCKER_ID: DEV_ARCH_CHECK_FORMAT_INVALID",
            "NEXT_ACTION_UNIQUE: DEV_FIX",
        ])
        (self.state_dir / "dev.last_contract").write_text(contract, encoding="utf-8")
        evaluate_policy(self._config(), now_epoch=1772800000)
        result = evaluate_policy(self._config(), now_epoch=1772800300)
        self.assertTrue(any(intent.target == "admin" and intent.reason == "contract_guard_escalation" for intent in result.intents))

    def test_stale_contract_guard_block_is_ignored(self) -> None:
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        self.report_path.write_text(json.dumps({}), encoding="utf-8")
        self.board_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
        contract_path = self.state_dir / "dev.last_contract"
        contract_path.write_text("\n".join([
            "STATUS: BLOCKED",
            "DELTA: CONTRACT_GUARD_BLOCK",
            "EVIDENCE: task_update=blocked; lock_check=ok; run_note=blocked by guard; issues=contract_guard_dev_arch_check_format_invalid; issue_count=1; issue_severity=high",
            "RISKS: invalid arch check",
            "NEXT: owner=dev; action=fix",
            "VERDICT: BLOCKED",
            "BLOCKER_ID: DEV_ARCH_CHECK_FORMAT_INVALID",
            "NEXT_ACTION_UNIQUE: DEV_FIX",
        ]), encoding="utf-8")
        old_epoch = 1772800000 - 7200
        os.utime(contract_path, (old_epoch, old_epoch))
        result = evaluate_policy(self._config(), now_epoch=1772800000)
        self.assertFalse(any(intent.reason == "contract_guard_block" for intent in result.intents))

    def test_stalled_in_progress_escalation_changes_reason_code(self) -> None:
        self.queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        self.report_path.write_text(json.dumps({}), encoding="utf-8")
        self.board_path.write_text(json.dumps({"tasks": [{"id": "BATCH-11-ARCH", "role": "planner", "state": "IN_PROGRESS", "updated_at": "2026-03-06T00:00:00Z"}]}), encoding="utf-8")
        first = evaluate_policy(self._config(), now_epoch=1772800000)
        second = evaluate_policy(self._config(), now_epoch=1772800300)
        self.assertTrue(any(intent.reason == "stalled_in_progress" for intent in first.intents))
        self.assertTrue(any(intent.reason == "stalled_in_progress_escalation" for intent in second.intents))


if __name__ == "__main__":
    unittest.main()
