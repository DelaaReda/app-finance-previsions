#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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
    previous_contract: str | None = None,
    env_extra: dict[str, str] | None = None,
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
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        if previous_contract is not None:
            state_dir = workdir / "role-state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / f"{role}.last_contract").write_text(previous_contract, encoding="utf-8")
            env["TMUX_ROLE_STATE_DIR"] = str(state_dir)
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
            env=env,
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

    def test_blocks_delivery_claim_when_reflection_evidence_missing(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_DEV_CLAIM_BATCH_02",
                (
                    "EVIDENCE: task_update=claim; lock_check=ok; "
                    "run_note=claim dev en cours avec preannounce valide; "
                    "exec_report=claim_prepare_et_scope_identifie; issues=none; suggestions=none; "
                    "arch_rule=api_contract; review_scope=BATCH-02-DEV; conformance=PASS; violations=none; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV; "
                    "intent_id=INTENT_DEV_UTEST; intent_chat_ref=chat#1; intent_memory_ref=memory#1; "
                    "intent_registry_ref=intent-registry#INTENT_DEV_UTEST; edit_scope=copilot-app/backend/src"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=claim_batch02_dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_CLAIM_REFLECTION_MISSING_UTEST",
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
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: REFLECTION_PASSES_INVALID", cp.stdout)

    def test_accepts_delivery_claim_with_reflection_evidence(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_DEV_CLAIM_BATCH_02",
                (
                    "EVIDENCE: task_update=claim; lock_check=ok; "
                    "run_note=claim dev avec cinq passes de reflexion explicites; "
                    "exec_report=claim_prepare_et_scope_identifie; issues=none; suggestions=none; "
                    "arch_rule=api_contract; review_scope=BATCH-02-DEV; conformance=PASS; violations=none; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV; "
                    "intent_id=INTENT_DEV_UTEST; intent_chat_ref=chat#1; intent_memory_ref=memory#1; "
                    "intent_registry_ref=intent-registry#INTENT_DEV_UTEST; edit_scope=copilot-app/backend/src; "
                    "reflection_passes=5; reflection_dimensions=scope,dependency_impact,risk,verification,rollback"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=claim_batch02_dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_CLAIM_REFLECTION_OK_UTEST",
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
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)

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

    def test_planner_converts_unverified_permission_claim_to_probe_continue(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: TASK_COMPLETE_FAILED_PERMISSION_DENIED_ON_LOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=tentative complete planner suivie d un faux blocage lock; "
                    "exec_report=complete_workboard_echoue_sur_lock_uniquement; "
                    "issues=permission_denied_lock_only; suggestions=reprendre_complete_sur_cmd_metier_reel; "
                    "channels_read=workboard_tasks,workboard_events; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=forecast_contract; review_scope=BATCH-02-PLAN; conformance=BLOCKED; violations=permission_denied_lock; "
                    "vision_rule=forecast-first; planner_artifact=tasks_md_update; stream_id=BATCH-02; task_id=BATCH-02-PLAN"
                ),
                "RISKS: permission denied on lock path",
                "NEXT: owner=planner; action=reprendre_complete_batch02_plan",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: PERMISSION_DENIED_PARALLEL_WORKSTREAM_LOCK",
                "NEXT_ACTION_UNIQUE: PLANNER_PERMISSION_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("DELTA: DELIVERY_PROBE_INCONSISTENT_CONTINUE", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("probe_reason=", cp.stdout)

    def test_delivery_probe_streak_escalates_after_threshold(self) -> None:
        previous_contract = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DELIVERY_PROBE_INCONSISTENT_CONTINUE",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; run_note=faux signal lock ignore, reprise livraison exigee; "
                    "exec_report=delivery_probe_inconsistent_lock_only; issues=none; suggestions=executer_cmd_metier_reelle_et_fermer_tache; "
                    "stream_id=BATCH-02; task_id=BATCH-02-DEV; tool_request=none; skill_request=none; channels_read=runtime_context; "
                    "impact_assessment=low; impact_action=resume_delivery; arch_rule=api_contract; review_scope=dev_delivery_probe; "
                    "conformance=WARN; violations=lock_probe_false_positive; dev_artifact=delivery_probe_lock_false_positive; "
                    "queue_version=queue_v_prev; workboard_version=workboard_v_prev; coordination_ref=resume_delivery:BATCH-02-DEV; "
                    "probe_reason=prev; delivery_probe_streak=2/3"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=executer_cmd_metier_reel_puis_complete_ou_handoff",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: RECHECK_DELIVERY_PROBE_DEV_PREV",
            ]
        )
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
                    "cmd_err_excerpt=permission denied; stream_id=BATCH-02; task_id=BATCH-02-DEV; "
                    "channels_read=workboard_tasks,workboard_events; impact_assessment=medium; impact_action=sync_cross_role"
                ),
                "RISKS: write blocked",
                "NEXT: owner=adminapp-codex; action=verifier_fs_permissions",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: WRITE_PERMISSION_BLOCKED",
                "NEXT_ACTION_UNIQUE: DEV_PERMISSION_STREAK_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state=None,
            previous_contract=previous_contract,
            env_extra={"TMUX_ROLE_DELIVERY_PROBE_THRESHOLD": "3"},
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("DELTA: DELIVERY_PROBE_STREAK_EXCEEDED", cp.stdout)
        self.assertIn("BLOCKER_ID: DELIVERY_PROBE_STREAK_EXCEEDED", cp.stdout)
        self.assertIn("delivery_probe_streak=3/3", cp.stdout)

    def test_planner_handoff_without_target_autofills_dev(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_PLANNER_HANDOFF_BATCH_08",
                (
                    "EVIDENCE: task_update=handoff; lock_check=ok; "
                    "run_note=handoff planner valide vers lane delivery apres verification architecture complete; "
                    "exec_report=handoff_prepare_batch08_vers_dev; issues=none; suggestions=none; "
                    "channels_read=workboard_tasks,workboard_events; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=forecast_contract; review_scope=BATCH-08-ANALYSIS; conformance=PASS; violations=none; "
                    "vision_rule=forecast-first; planner_artifact=docs/operations/orchestrator/priority-queue.json; "
                    "stream_id=BATCH-08; task_id=BATCH-08-ANALYSIS"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=claim BATCH-08-DEV-01",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLANNER_HANDOFF_NO_TARGET_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("handoff_to=dev", cp.stdout)

    def test_planner_handoff_missing_blocker_is_converted_to_wait(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: CONTRACT_GUARD_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=guard signale handoff sans cible explicite et lane doit rester active; "
                    "exec_report=guard_block_detected_handoff_target_missing; issues=handoff_to_missing; suggestions=normalize_target; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=forecast_contract; review_scope=BATCH-08-ANALYSIS; conformance=BLOCKED; violations=handoff_to_missing; "
                    "vision_rule=forecast-first; planner_artifact=platform/policies/role_contract_guard.py; "
                    "stream_id=BATCH-08; task_id=BATCH-08-ANALYSIS"
                ),
                "RISKS: handoff target missing",
                "NEXT: owner=planner; action=fix contract",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: HANDOFF_TO_MISSING",
                "NEXT_ACTION_UNIQUE: PLANNER_HANDOFF_BLOCKED_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: WAIT", cp.stdout)
        self.assertIn("DELTA: NO_DELTA", cp.stdout)
        self.assertIn("VERDICT: PASS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("handoff_to_autofill=dev", cp.stdout)
        self.assertIn("WAIT_HANDOFF_TARGET_NORMALIZED_", cp.stdout)


    def test_planner_blocked_batch_id_invalid_is_converted_to_wait(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: CONTRACT_GUARD_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=guard detecte batch id invalide mais lane planner doit rester active; "
                    "planner_artifact=platform/policies/role_contract_guard.py; "
                    "stream_id=BATCH-08; task_id=BATCH-08-ANALYSIS"
                ),
                "RISKS: batch id invalid",
                "NEXT: owner=planner; action=fix batch id",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: PLANNER_BATCH_ID_INVALID",
                "NEXT_ACTION_UNIQUE: PLANNER_BATCH_INVALID_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: WAIT", cp.stdout)
        self.assertIn("DELTA: NO_DELTA", cp.stdout)
        self.assertIn("VERDICT: PASS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("batch_created_sanitized=1", cp.stdout)

    def test_planner_blocked_mode_analyse_is_converted_to_wait(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: MODE_ANALYSE_BLOQUE_CREATION_BATCH",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=mode analyse sans edits force un faux blocage planner; "
                    "planner_artifact=platform/policies/role_contract_guard.py; "
                    "stream_id=BATCH-08; task_id=BATCH-08-ANALYSIS"
                ),
                "RISKS: mode analyse",
                "NEXT: owner=planner; action=switch delivery",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: MODE_ANALYSE_NO_EDITS",
                "NEXT_ACTION_UNIQUE: PLANNER_MODE_ANALYSE_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: WAIT", cp.stdout)
        self.assertIn("DELTA: NO_DELTA", cp.stdout)
        self.assertIn("VERDICT: PASS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("analysis_mode_converted_wait=1", cp.stdout)


if __name__ == "__main__":
    unittest.main()
