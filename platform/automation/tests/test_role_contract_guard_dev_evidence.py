#!/usr/bin/env python3
from __future__ import annotations

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
    role: str = "dev",
    allow_file_edits: str = "1",
    workboard_has_work: str = "1",
    workboard_has_in_progress: str = "1",
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
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


def payload_with_evidence(evidence: str) -> str:
    return "\n".join(
        [
            "STATUS: IN_PROGRESS",
            "DELTA: TASK_DEV_DELIVERY",
            f"EVIDENCE: {evidence}",
            "RISKS: none",
            "NEXT: owner=dev; action=continue delivery",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: DEV_EVIDENCE_UTEST",
        ]
    )


class RoleContractGuardDevEvidenceTests(unittest.TestCase):
    def test_claim_allows_lightweight_payload_with_placeholder_root_cause(self) -> None:
        payload = payload_with_evidence(
            "task_update=claim; lock_check=ok; "
            "run_note=claim dev avec verification architecture appliquee; "
            "dev_artifact=apps/api/src/domains/copilot/application/copilot_service.py; "
            "stream_id=BATCH-26; task_id=BATCH-26-DEV-02; "
            "root_cause=?; "
            "reflection_passes=2; reflection_dimensions=scope,dependency_impact,risk,verification,rollback; "
            "architecture_check=layer=application,imports_ok=yes,path_target=apps/api/src/domains/copilot/application/copilot_service.py; "
            "vision_alignment=batch=BATCH-26,target=copilot_runtime,impact=delivery_ready; "
            "reuse_check=domains.judge.application.g4f_client"
        )
        cp = run_guard(payload)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)

    def test_complete_blocks_invalid_verify_format(self) -> None:
        payload = payload_with_evidence(
            "task_update=complete; lock_check=ok; "
            "run_note=complete dev avec preuve partielle detectee; "
            "dev_artifact=apps/api/src/domains/copilot/application/copilot_service.py; "
            "root_cause=import path non resilient sur llm client; "
            "fix_applied=correction import absolu vers module reuse; "
            "verify=before=llm_fallback,after=llm_primary; "
            "reuse_check=domains.judge.application.g4f_client; "
            "architecture_check=layer=application,imports_ok=yes,path_target=apps/api/src/domains/copilot/application/copilot_service.py; "
            "vision_alignment=batch=BATCH-26,target=delivery_stable,impact=api_unblocked; "
            "qa_proof=test=pytest platform/tests,result=PASS; "
            "cmd=pytest platform/tests -q; tests_run=unit:PASS"
        )
        cp = run_guard(payload)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: DEV_VERIFY_FORMAT_INVALID", cp.stdout)

    def test_complete_blocks_invalid_qa_proof_format(self) -> None:
        payload = payload_with_evidence(
            "task_update=complete; lock_check=ok; "
            "run_note=complete dev avec qa proof incomplte detectee; "
            "dev_artifact=apps/api/src/domains/copilot/application/copilot_service.py; "
            "root_cause=service copilot n injecte pas contexte propre; "
            "fix_applied=ajout injection contexte dans payload ask; "
            "verify=before=fallback_only,after=primary_with_context,test=pytest platform/tests; "
            "reuse_check=domains.judge.application.g4f_client; "
            "architecture_check=layer=application,imports_ok=yes,path_target=apps/api/src/domains/copilot/application/copilot_service.py; "
            "vision_alignment=batch=BATCH-26,target=delivery_stable,impact=user_answer_quality; "
            "qa_proof=test=pytest platform/tests; "
            "cmd=pytest platform/tests -q; tests_run=unit:PASS"
        )
        cp = run_guard(payload)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: DEV_QA_PROOF_FORMAT_INVALID", cp.stdout)

    def test_complete_blocks_reuse_none_without_reason(self) -> None:
        payload = payload_with_evidence(
            "task_update=complete; lock_check=ok; "
            "run_note=complete dev avec reutilisation non justifiee; "
            "dev_artifact=apps/api/src/domains/copilot/application/copilot_service.py; "
            "root_cause=module ancien non resolu lors du runtime; "
            "fix_applied=chemin module aligne avec architecture cible; "
            "verify=before=module_missing,after=module_loaded,test=pytest platform/tests; "
            "reuse_check=NONE; "
            "architecture_check=layer=application,imports_ok=yes,path_target=apps/api/src/domains/copilot/application/copilot_service.py; "
            "vision_alignment=batch=BATCH-26,target=delivery_stable,impact=runtime_clean; "
            "qa_proof=test=pytest platform/tests,result=PASS; "
            "cmd=pytest platform/tests -q; tests_run=unit:PASS"
        )
        cp = run_guard(payload)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: BLOCKED", cp.stdout)
        self.assertIn("BLOCKER_ID: DEV_REUSE_CHECK_INVALID", cp.stdout)

    def test_complete_accepts_strong_evidence(self) -> None:
        payload = payload_with_evidence(
            "task_update=complete; lock_check=ok; "
            "run_note=complete dev avec preuves concretes et verifiees; "
            "dev_artifact=apps/api/src/domains/copilot/application/copilot_service.py; "
            "stream_id=BATCH-26; task_id=BATCH-26-DEV-02; "
            "root_cause=fallback forcait un module legacy non maintenu; "
            "fix_applied=import direct module juge existant et suppression bridge local; "
            "verify=before=fallback_only,after=primary_with_context,test=pytest platform/tests/test_copilot.py; "
            "reuse_check=domains.judge.application.g4f_client; "
            "architecture_check=layer=application,imports_ok=yes,path_target=apps/api/src/domains/copilot/application/copilot_service.py; "
            "vision_alignment=batch=BATCH-26,target=delivery_stable,impact=reponse_plus_fiable; "
            "qa_proof=test=pytest platform/tests/test_copilot.py,result=PASS; "
            "cmd=pytest platform/tests/test_copilot.py -q; tests_run=unit:PASS"
        )
        cp = run_guard(payload)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)

    def test_complete_accepts_split_compound_evidence_fields(self) -> None:
        payload = payload_with_evidence(
            "task_update=complete; lock_check=ok; "
            "run_note=complete dev avec sous champs evidence separes correctement; "
            "dev_artifact=apps/api/src/domains/copilot/application/copilot_service.py; "
            "stream_id=BATCH-27; task_id=BATCH-27-DEV-02; "
            "root_cause=fallback forcait un module legacy non maintenu; "
            "fix_applied=import direct module juge existant et suppression bridge local; "
            "verify=before=fallback_only; after=primary_with_context; test=pytest platform/tests/test_copilot.py; "
            "reuse_check=domains.judge.application.g4f_client; "
            "architecture_check=layer=application; imports_ok=yes; path_target=apps/api/src/domains/copilot/application/copilot_service.py; "
            "vision_alignment=batch=BATCH-27; target=delivery_stable; impact=reponse_plus_fiable; "
            "qa_proof=test=pytest platform/tests/test_copilot.py; result=PASS; "
            "cmd=pytest platform/tests/test_copilot.py -q; tests_run=unit:PASS"
        )
        cp = run_guard(payload)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("STATUS: IN_PROGRESS", cp.stdout)
        self.assertIn("BLOCKER_ID: NONE", cp.stdout)


if __name__ == "__main__":
    unittest.main()
