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


def _normalize_issue_report_payload(payload: str) -> str:
    lines = payload.splitlines()
    status = ""
    blocker_id = ""
    for raw in lines:
        if raw.startswith("STATUS:"):
            status = raw.split(":", 1)[1].strip().upper()
        elif raw.startswith("BLOCKER_ID:"):
            blocker_id = raw.split(":", 1)[1].strip().upper()

    for idx, raw in enumerate(lines):
        if not raw.startswith("EVIDENCE:"):
            continue
        evidence = raw.split(":", 1)[1].strip()
        kv: dict[str, str] = {}
        order: list[str] = []
        for part in evidence.split(";"):
            seg = part.strip()
            if "=" not in seg:
                continue
            key, value = seg.split("=", 1)
            k = key.strip()
            if not k:
                continue
            if k not in kv:
                order.append(k)
            kv[k] = value.strip()

        issues = str(kv.get("issues", "none") or "none").strip()
        issues_l = issues.lower()
        blocked_like = status == "BLOCKED" or blocker_id not in {"", "NONE", "N/A", "NULL"}

        if issues_l in {"", "none"} and blocked_like:
            issues = "blocked_without_issue_report"
            issues_l = issues
        kv["issues"] = issues

        if "issue_count" not in kv:
            if issues_l == "none":
                kv["issue_count"] = "0"
            else:
                codes = [c.strip() for c in issues.split(",") if c.strip()]
                kv["issue_count"] = str(max(1, len(codes)))
                if "issue_count" not in order:
                    order.append("issue_count")

        if "issue_severity" not in kv:
            kv["issue_severity"] = "none" if issues_l == "none" else "medium"
            if "issue_severity" not in order:
                order.append("issue_severity")

        preferred = ["issues", "issue_count", "issue_severity"]
        out_parts: list[str] = []
        seen: set[str] = set()
        for key in order:
            if key in kv:
                out_parts.append(f"{key}={kv[key]}")
                seen.add(key)
        for key in preferred:
            if key in kv and key not in seen:
                out_parts.append(f"{key}={kv[key]}")
                seen.add(key)
        for key in sorted(kv.keys()):
            if key in seen:
                continue
            out_parts.append(f"{key}={kv[key]}")

        lines[idx] = "EVIDENCE: " + "; ".join(out_parts)
        break

    return "\n".join(lines)


def run_guard(
    payload: str,
    *,
    role: str,
    source: str = "unit_test",
    allow_file_edits: str,
    workboard_has_work: str,
    workboard_has_in_progress: str,
    queue_state: str | None,
    previous_contract: str | None = None,
    env_extra: dict[str, str] | None = None,
    normalize_issue_report: bool = True,
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
        payload_text = _normalize_issue_report_payload(payload) if normalize_issue_report else payload
        payload_file.write_text(payload_text, encoding="utf-8")
        env = os.environ.copy()
        if role == "dev":
            env.setdefault("FC_DEV_CHANNELS_IMPACT_AUTOFILL", "1")
            env.setdefault("FC_DEV_PERMISSIVE_GUARD", "1")
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
                source,
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

    def test_issue_report_valid_none_contract_passes(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLAN_BATCH_02_READY_FLOW",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse priorite et verification de dependances lane planner; "
                    "exec_report=analyse_batch02_realisee_avec_dependances; issues=none; issue_count=0; issue_severity=none; suggestions=none; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-PLAN; conformance=PASS; violations=none; "
                    "vision_rule=forecast-first; planner_artifact=plan_batch02_refresh; "
                    "stream_id=BATCH-02; task_id=BATCH-02-PLAN"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=preparer_patch_backend",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLAN_BATCH02_ISSUE_OK_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={"FC_SCRUM_MASTER_MODE": "advisory"},
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)

    def test_planner_quality_missing_soft_autofix_non_blocking(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: READY_ITEM_AVAILABLE_RUNTIME_CONTEXT",
                (
                    "EVIDENCE: task_update=claim; lock_check=ok; "
                    "run_note=planner claim dispatch maintenant avec preuves minimales; "
                    "planner_artifact=docs/operations/orchestrator/planner-note.md; "
                    "stream_id=BATCH-11; task_id=BATCH-11-PLAN; "
                    "channels_read=workboard_tasks; impact_assessment=low; impact_action=sync_cross_role; "
                    "root_cause=none; fix_applied=none; verify=none; reuse_check=none; "
                    "issues=none; issue_count=0; issue_severity=none"
                ),
                "RISKS: none",
                "NEXT: owner=planner; action=claim_or_progress_now",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLANNER_QUALITY_SOFT_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={"PLANNER_QUALITY_SOFT_ENFORCE": "1"},
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("DELTA: PLANNER_QUALITY_INCOMPLETE", cp.stdout)
        self.assertIn("VERDICT: GO_WITH_CAUTION", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("planner_quality_autofix=1", cp.stdout)
        self.assertIn("planner_quality_missing=", cp.stdout)

    def test_issue_report_missing_fields_blocks(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLAN_BATCH_02_READY_FLOW",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse planner complete sans champs issue obligatoires; "
                    "issues=none; planner_artifact=plan_batch02_refresh; "
                    "stream_id=BATCH-02; task_id=BATCH-02-PLAN; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-PLAN; conformance=PASS; violations=none; vision_rule=forecast-first"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=preparer_patch_backend",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLAN_BATCH02_ISSUE_MISSING_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: ISSUE_REPORT_MISSING", cp.stdout)

    def test_issue_report_inconsistent_count_blocks(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLAN_BATCH_02_READY_FLOW",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse planner avec report issue incoherent volontaire; "
                    "issues=cache_miss,upstream_timeout; issue_count=1; issue_severity=high; "
                    "planner_artifact=plan_batch02_refresh; stream_id=BATCH-02; task_id=BATCH-02-PLAN; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-PLAN; conformance=PASS; violations=none; vision_rule=forecast-first"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=preparer_patch_backend",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLAN_BATCH02_ISSUE_COUNT_BAD_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: ISSUE_REPORT_INCONSISTENT", cp.stdout)

    def test_blocked_without_issue_report_blocks(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: CONTRACT_GUARD_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=blocage sans report issue valide pour test guard; "
                    "issues=none; issue_count=0; issue_severity=none; "
                    "planner_artifact=plan_batch02_refresh; stream_id=BATCH-02; task_id=BATCH-02-PLAN; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-PLAN; conformance=BLOCKED; violations=runtime; vision_rule=forecast-first"
                ),
                "RISKS: blocked",
                "NEXT: owner=planner; action=corriger report issue",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: RUNTIME_BLOCKER",
                "NEXT_ACTION_UNIQUE: PLAN_BATCH02_ISSUE_BLOCKED_BAD_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: BLOCKED_WITHOUT_ISSUE_REPORT", cp.stdout)

    def test_issue_report_invalid_severity_blocks(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: PLAN_BATCH_02_READY_FLOW",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse planner avec severite issue invalide; "
                    "issues=cache_miss; issue_count=1; issue_severity=severe; "
                    "planner_artifact=plan_batch02_refresh; stream_id=BATCH-02; task_id=BATCH-02-PLAN; "
                    "channels_read=workboard_tasks,admin_chat; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=api_contract; review_scope=BATCH-02-PLAN; conformance=PASS; violations=none; vision_rule=forecast-first"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=preparer_patch_backend",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLAN_BATCH02_ISSUE_SEV_BAD_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: ISSUE_REPORT_INVALID", cp.stdout)

    def test_blocks_channels_fields_when_missing_on_normal_output(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
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
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("channels_autofill_missing", cp.stdout)

    def test_blocks_channels_when_channels_read_is_none_on_normal_output(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
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
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("channels_autofill_missing", cp.stdout)

    def test_blocks_impact_action_when_medium_has_none_on_normal_output(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
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
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("impact_autofill_missing", cp.stdout)

    def test_blocks_when_high_impact_has_no_action_on_normal_output(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
                    "run_note=analyse lane active avec impact eleve sans action concrete; "
                    "issues=none; issue_count=0; issue_severity=none; "
                    "channels_read=runtime_context,workboard_tasks; impact_assessment=high; impact_action=none; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=ajouter impact_action",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_IMPACT_HIGH_NONE_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("impact_autofill_missing", cp.stdout)

    def test_dev_issue_report_incomplete_code_used_when_issue_fields_missing(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_BATCH_02_DEV_DELIVERY",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
                    "run_note=dev oublie une partie du report issue obligatoire; "
                    "issues=none; channels_read=workboard_tasks,workboard_events; "
                    "impact_assessment=low; impact_action=monitor_updates; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=corriger contrat issue",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_ISSUE_INCOMPLETE_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: DEV_ISSUE_REPORT_INCOMPLETE", cp.stdout)

    def test_dev_enforced_action_missing_blocks_when_guard_active(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: NO_DELTA",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
                    "run_note=sortie passive alors que guard autonomy est actif; "
                    "issues=none; issue_count=0; issue_severity=none; "
                    "channels_read=runtime_context,workboard_tasks; impact_assessment=low; impact_action=monitor_updates; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=wait",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_ENFORCED_MISSING_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
            env_extra={
                "DEV_AUTONOMY_ENFORCE_GUARD": "1",
                "DEV_AUTONOMY_NONE_STREAK": "3",
                "TMUX_ROLE_DEV_AUTONOMY_STALL_THRESHOLD_TICKS": "2",
                "RUNTIME_QUEUE_HAS_READY": "1",
            },
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: DEV_ENFORCED_ACTION_MISSING", cp.stdout)

    def test_dev_stall_with_actionable_work_blocks_on_repeated_none(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: NO_DELTA",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
                    "run_note=sortie passive repetee avec travail actionnable; "
                    "issues=none; issue_count=0; issue_severity=none; "
                    "channels_read=runtime_context,workboard_tasks; impact_assessment=low; impact_action=monitor_updates; "
                    "dev_artifact=dev_scope_batch02; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=wait",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_BATCH02_STALL_WITH_WORK_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
            env_extra={
                "DEV_AUTONOMY_ENFORCE_GUARD": "0",
                "DEV_AUTONOMY_NONE_STREAK": "6",
                "TMUX_ROLE_DEV_AUTONOMY_STALL_THRESHOLD_TICKS": "2",
                "TMUX_ROLE_DEV_WAIT_ROLE_SCOPED": "0",
                "RUNTIME_QUEUE_HAS_READY": "1",
            },
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: DEV_STALL_WITH_ACTIONABLE_WORK", cp.stdout)

    def test_dev_analysis_only_with_ready_adds_passive_issue(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: READY_ITEM_AVAILABLE_RUNTIME_CONTEXT",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=analyse rapide avant claim imminent avec ready present; "
                    "issues=none; issue_count=0; issue_severity=none; "
                    "channels_read=runtime_context,workboard_tasks; impact_assessment=low; impact_action=monitor_updates; "
                    "dev_artifact=dev_scope_batch55; stream_id=BATCH-55; task_id=BATCH-55-DEV-01"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=claim_or_progress_now",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_PASSIVE_WITH_READY_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
            env_extra={
                "DEV_AUTONOMY_ENFORCE_GUARD": "0",
                "DEV_AUTONOMY_NONE_STREAK": "0",
                "TMUX_ROLE_DEV_WAIT_ROLE_SCOPED": "0",
                "RUNTIME_QUEUE_HAS_READY": "1",
            },
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("issues=dev_passive_with_ready", cp.stdout.lower())

    def test_accepts_fallback_channels_autofill_payload(self) -> None:
        payload = "\n".join(
            [
                "STATUS: WAIT",
                "DELTA: RATE_LIMIT_BACKOFF",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
                    "run_note=backoff technique avec autofill channels pour fallback runtime; "
                    "issues=rate_limit_detected,channels_autofill_fallback; issue_count=2; issue_severity=medium; "
                    "channels_read=runtime_context; impact_assessment=low; impact_action=monitor_updates; "
                    "dev_artifact=rate_limit_gate; stream_id=RATELIMIT_dev; task_id=RATELIMIT_dev"
                ),
                "RISKS: quota temporaire",
                "NEXT: owner=admin; action=attendre fin cooldown",
                "VERDICT: WAIT",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_FALLBACK_CHANNELS_AUTOFILL_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            source="rate_limit_gate_probe",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="0",
            queue_state="READY",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: WAIT", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)

    def test_blocked_runtime_with_valid_issue_report_passes(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: DEV_RUNTIME_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=blocage runtime confirme avec preuve de quota reelle; "
                    "issues=agent_rate_limit_codex; issue_count=1; issue_severity=high; "
                    "channels_read=runtime_context; impact_assessment=medium; impact_action=wait_for_quota_recovery; "
                    "dev_artifact=platform/automation/cron_tmux_role_runner.sh; "
                    "stream_id=BATCH-26; task_id=BATCH-26-DEV-02; "
                    "cmd=python3 platform/automation/parallel_workstream.py status --role dev --compact; "
                    "cmd_err_excerpt=http_429_quota"
                ),
                "RISKS: quota",
                "NEXT: owner=admin; action=wait_then_retry",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: AGENT_RATE_LIMIT_CODEX",
                "NEXT_ACTION_UNIQUE: DEV_RUNTIME_BLOCK_ISSUE_VALID_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("dev_permissive_guard_normalized", cp.stdout)

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
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("DELTA: DELIVERY_PROBE_STREAK_EXCEEDED", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
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

    def test_planner_handoff_placeholder_target_autofills_dev(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: TASK_PLANNER_HANDOFF_BATCH_08",
                (
                    "EVIDENCE: task_update=handoff; lock_check=ok; "
                    "run_note=handoff planner vers lane delivery apres verification architecture complete; "
                    "exec_report=handoff_prepare_batch08_vers_dev; issues=none; suggestions=none; "
                    "channels_read=workboard_tasks,workboard_events; impact_assessment=medium; impact_action=sync_cross_role; "
                    "arch_rule=forecast_contract; review_scope=BATCH-08-ANALYSIS; conformance=PASS; violations=none; "
                    "vision_rule=forecast-first; planner_artifact=docs/operations/orchestrator/priority-queue.json; "
                    "stream_id=BATCH-08; task_id=BATCH-08-ANALYSIS; handoff_to=?"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=claim BATCH-08-DEV-01",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLANNER_HANDOFF_PLACEHOLDER_TARGET_UTEST",
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

    def test_blocked_contract_uses_role_specific_artifact_key(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DEV_RUNTIME_CHECK",
                (
                    "EVIDENCE: task_update=analysis_only; "
                    "run_note=analyse dev sans lock check explicite pour valider guard output; "
                    "exec_report=dev_precheck_runtime; issues=none; suggestions=none; "
                    "dev_artifact=apps/api/src/platform/main.py; stream_id=BATCH-02; task_id=BATCH-02-DEV"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=continue",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_LOCKCHECK_MISSING_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: LOCK_CHECK_MISSING", cp.stdout)
        self.assertIn("dev_artifact=platform/policies/role_contract_guard.py", cp.stdout)
        self.assertNotIn("role_artifact=contract_guard", cp.stdout)

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

    def test_planner_blocked_waiting_dep_chain_is_converted_to_wait(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: CONTRACT_GUARD_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=dependencies chain waiting detected but planner lane must stay active; "
                    "planner_artifact=platform/policies/role_contract_guard.py; "
                    "stream_id=BATCH-27; task_id=BATCH-27-PLAN"
                ),
                "RISKS: dependency waiting chain",
                "NEXT: owner=planner; action=advance root task",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: BLOCKED_BY_MULTI_WAITING_DEPENDENCIES",
                "NEXT_ACTION_UNIQUE: PLANNER_DEP_CHAIN_UTEST",
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
        self.assertIn("waiting_dep_softblock_normalized=1", cp.stdout)

    def test_planner_waiting_dependencies_soft_blocker_is_normalized(self) -> None:
        payload = "\n".join(
            [
                "STATUS: WAIT",
                "DELTA: IN_PROGRESS_BLOCKED_WAITING_DEPENDENCIES",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=planner detecte waiting dependencies mais lane doit rester active; "
                    "planner_artifact=docs/operations/orchestrator/parallel-workstreams.json; "
                    "stream_id=BATCH-27; task_id=BATCH-27-PLAN"
                ),
                "RISKS: waiting dependencies",
                "NEXT: owner=planner; action=resume completion",
                "VERDICT: WAIT",
                "BLOCKER_ID: WAITING_DEPENDENCIES",
                "NEXT_ACTION_UNIQUE: PLANNER_WAIT_DEP_UTEST",
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
        self.assertIn("waiting_dep_softblock_normalized=1", cp.stdout)

    def test_planner_inter_batch_dependency_hint_is_normalized(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: NO_DELTA",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=planner propose dependance inter batch qui doit etre refusee; "
                    "planner_artifact=docs/operations/orchestrator/priority-queue.json; "
                    "batch_depends_on=BATCH-11; stream_id=BATCH-27; task_id=BATCH-27-PLAN"
                ),
                "RISKS: inter batch dependency",
                "NEXT: owner=planner; action=continuer",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLANNER_INTER_BATCH_DEP_UTEST",
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
        self.assertIn("dependency_policy_enforced=1", cp.stdout)
        self.assertIn("original_blocker=PLANNER_INTER_BATCH_DEP_FORBIDDEN", cp.stdout)

    def test_planner_passive_output_is_autofixed_when_runtime_is_healthy(self) -> None:
        payload = "\n".join(
            [
                "STATUS: WAIT",
                "DELTA: NO_DELTA",
                (
                    "EVIDENCE: task_update=none_no_ready; lock_check=ok; "
                    "run_note=planner reste passif alors que la policy impose progression active; "
                    "planner_artifact=docs/operations/orchestrator/parallel-workstreams.json; "
                    "issues=none; issue_count=0; issue_severity=none"
                ),
                "RISKS: none",
                "NEXT: owner=planner; action=wait",
                "VERDICT: PASS",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLANNER_PASSIVE_AUTOFIX_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={
                "TMUX_ROLE_PLANNER_NEVER_WAIT": "1",
                "TMUX_ROLE_PLANNER_RUNTIME_FORCE_UP": "1",
            },
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("DELTA: PLANNER_PROGRESS_REQUIRED", cp.stdout)
        self.assertIn("VERDICT: GO_WITH_CAUTION", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("planner_passive_autofix=1", cp.stdout)
        self.assertIn("planner_non_passive_policy=enforced", cp.stdout)
        self.assertIn("planner_action_required=create_or_claim", cp.stdout)

    def test_planner_runtime_exception_allows_passive_none_no_signal(self) -> None:
        payload = "\n".join(
            [
                "STATUS: WAIT",
                "DELTA: RUNTIME_DEGRADED",
                (
                    "EVIDENCE: task_update=none_no_signal; lock_check=ok; "
                    "run_note=runtime down detecte, attente planifier recovery; "
                    "planner_artifact=docs/operations/orchestrator/parallel-workstreams.json; "
                    "issues=backend_api_unreachable; issue_count=1; issue_severity=high"
                ),
                "RISKS: runtime down",
                "NEXT: owner=planner; action=wait runtime",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: BACKEND_API_UNREACHABLE",
                "NEXT_ACTION_UNIQUE: PLANNER_RUNTIME_EXCEPTION_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={"TMUX_ROLE_PLANNER_NEVER_WAIT": "1"},
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("DELTA: RUNTIME_UNAVAILABLE", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("planner_runtime_exception=1", cp.stdout)
        self.assertIn("issues=runtime_unavailable", cp.stdout)

    def test_dev_none_no_ready_allowed_when_only_global_queue_ready(self) -> None:
        payload = "\n".join(
            [
                "STATUS: WAIT",
                "DELTA: NO_DELTA",
                (
                    "EVIDENCE: task_update=none_no_ready; lock_check=ok; "
                    "run_note=lane dev vide, attente role-scoped autorisee pour prochain claim; "
                    "dev_artifact=docs/product/planning/tasks.md; "
                    "channels_read=runtime_context,workboard_tasks; impact_assessment=low; impact_action=monitor_updates; "
                    "issues=none; issue_count=0; issue_severity=none"
                ),
                "RISKS: none",
                "NEXT: owner=dev; action=attendre task dev READY",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: DEV_ROLE_SCOPED_WAIT_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="dev",
            allow_file_edits="1",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={
                "TMUX_ROLE_DEV_WAIT_ROLE_SCOPED": "1",
                "RUNTIME_QUEUE_HAS_READY": "1",
            },
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertNotIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)

    def test_scrum_master_contract_is_forced_non_blocking(self) -> None:
        payload = "\n".join(
            [
                "STATUS: BLOCKED",
                "DELTA: CONTRACT_GUARD_BLOCK",
                (
                    "EVIDENCE: task_update=blocked; lock_check=ok; "
                    "run_note=scrum advisory reporte un blocage mais ne doit pas stopper le runtime; "
                    "scrum_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md"
                ),
                "RISKS: advisory blocked",
                "NEXT: owner=scrum_master; action=investiguer",
                "VERDICT: BLOCKED",
                "BLOCKER_ID: CHANNELS_READ_MISSING",
                "NEXT_ACTION_UNIQUE: SCRUM_BLOCKED_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="scrum_master",
            allow_file_edits="0",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={"FC_SCRUM_MASTER_MODE": "advisory"},
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("VERDICT: GO_WITH_CAUTION", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("advisory_non_blocking=1", cp.stdout)


    def test_planner_evidence_incomplete_is_soft_non_blocking(self) -> None:
        payload = "\n".join(
            [
                "STATUS: IN_PROGRESS",
                "DELTA: DELIVERY",
                (
                    "EVIDENCE: task_update=complete; lock_check=ok; "
                    "run_note=planner finalize sans verify complet pour test guard soft; "
                    "stream_id=BATCH-88; task_id=BATCH-88-PLAN; cmd=python3 -m pytest -q; "
                    "planner_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md; issues=none; issue_count=0; issue_severity=none"
                ),
                "RISKS: medium",
                "NEXT: owner=planner; action=handoff dev",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: PLANNER_EVIDENCE_SOFT_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="planner",
            allow_file_edits="0",
            workboard_has_work="1",
            workboard_has_in_progress="1",
            queue_state="IN_PROGRESS",
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("VERDICT: GO_WITH_CAUTION", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertIn("planner_evidence_incomplete_soft", cp.stdout)

    def test_scrum_artifact_missing_is_autofilled_non_blocking(self) -> None:
        payload = "\n".join(
            [
                "STATUS: WAIT",
                "DELTA: NO_DELTA",
                (
                    "EVIDENCE: task_update=analysis_only; lock_check=ok; "
                    "run_note=scrum advisory audit sans artifact explicite pour test autofill"
                ),
                "RISKS: low",
                "NEXT: owner=scrum_master; action=publish advisory",
                "VERDICT: GO_WITH_CAUTION",
                "BLOCKER_ID: NONE",
                "NEXT_ACTION_UNIQUE: SCRUM_ARTIFACT_AUTOFILL_UTEST",
            ]
        )
        cp = run_guard(
            payload,
            role="scrum_master",
            allow_file_edits="0",
            workboard_has_work="0",
            workboard_has_in_progress="0",
            queue_state="READY",
            env_extra={
                "FC_SCRUM_MASTER_MODE": "advisory",
                "FC_SCRUM_ARTIFACT_AUTOFILL": "1",
            },
            normalize_issue_report=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("scrum_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)
        self.assertNotIn("STATUS: BLOCKED", cp.stdout)


if __name__ == "__main__":
    unittest.main()
