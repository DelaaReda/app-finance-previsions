#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "role_contract_guard.py"


def run_guard(
    payload: str,
    *,
    role: str,
    allow_file_edits: str,
    workboard_has_work: str,
    workboard_has_in_progress: str,
    queue_state: str | None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        queue_dir = workdir / "docs" / "orchestrator-ops"
        queue_dir.mkdir(parents=True, exist_ok=True)
        if queue_state is None:
            queue_payload = {"items": []}
        else:
            queue_payload = {"items": [{"id": "BATCH-02", "state": queue_state}]}
        (queue_dir / "priority-queue.json").write_text(json.dumps(queue_payload), encoding="utf-8")
        payload_file = workdir / "payload.txt"
        payload_file.write_text(payload, encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(GUARD),
                role,
                "unit_test",
                str(payload_file),
                allow_file_edits,
                workboard_has_work,
                workboard_has_in_progress,
                "queue_v_test",
                "workboard_v_test",
            ],
            cwd=workdir,
            text=True,
            capture_output=True,
            check=False,
        )


class RoleContractGuardTests(unittest.TestCase):
    def test_accepts_valid_planner_contract_and_injects_versions(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLAN_BATCH_02_READY_FLOW",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse de la priorite et des impacts publication; "
                    "exec_report=analyse_batch02_realisee_avec_dependances; issues=none; suggestions=none; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-PLAN; conformance=PASS; violations=none; "
                    "vision_rule=forecast-first; planner_artifact=plan_batch02_refresh; "
                    "stream_id=BATCH-02; task_id=BATCH-02-PLAN"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=preparer_patch_backend",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLAN_BATCH02_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("queue_version=queue_v_test", cp.stdout)
        self.assertIn("workboard_version=workboard_v_test", cp.stdout)

    def test_blocks_when_channels_fields_are_missing(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse de tache dev sans lecture des canaux; "
                    "exec_report=analyse_dev_realisee; issues=none; suggestions=none; "
                    "arch_rule=api_contract; review_scope=BATCH-02-DEV; conformance=PASS; violations=none; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=tester; action=preparer_tests",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: CHANNELS_READ_MISSING", cp.stdout)

    def test_blocks_when_channels_read_is_none(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse publication mais canaux non explicites; "
                    "exec_report=analyse_dev_realisee; issues=none; suggestions=none; "
                    "channels_read=none; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-DEV; conformance=PASS; violations=none; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=tester; action=preparer_tests",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_CH_NONE_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: CHANNELS_READ_INVALID", cp.stdout)

    def test_blocks_when_medium_impact_has_no_action(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse impact cross role sans action concrete; "
                    "exec_report=analyse_dev_realisee; issues=none; suggestions=none; "
                    "channels_read=workboard_tasks,workboard_events; impact_assessment=medium; impact_action=none; "
                    "arch_rule=api_contract; review_scope=BATCH-02-DEV; conformance=PASS; violations=none; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=tester; action=preparer_tests",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_IMPACT_NONE_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: IMPACT_ACTION_INSUFFICIENT", cp.stdout)

    def test_converts_unverified_permission_claim_to_probe_continue(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: TASK_WRITE_PERMISSION_DENIED",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=tentative d ecriture puis permission denied recue; "
                    "exec_report=echec_ecriture_dev; issues=permission_denied; suggestions=verifier_droits_volume; "
                    "arch_rule=api_contract; review_scope=BATCH-02-DEV; conformance=BLOCKED; violations=permission; "
                    "dev_artifact=write_attempt_batch02; cmd=python3 write.py permission denied; "
                    "cmd_err_excerpt=permission denied"
                ),
                "RISKS: write blocked",
                "NEXT: owner=adminapp-codex; action=verifier_fs_permissions",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: WRITE_PERMISSION_BLOCKED",
                "NEXT_ACTION_UNIQUE: DEV_PERMISSION_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state=None,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        delta_ok = (
            "DELTA: PERMISSION_PROBE_CONTINUE" in cp.stdout
            or "DELTA: DELIVERY_PROBE_INCONSISTENT_CONTINUE" in cp.stdout
        )
        self.assertTrue(delta_ok, msg=cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        evidence_ok = (
            "permission_probe=unverified_continue" in cp.stdout
            or "probe_reason=" in cp.stdout
        )
        self.assertTrue(evidence_ok, msg=cp.stdout)


if __name__ == "__main__":
    unittest.main()
