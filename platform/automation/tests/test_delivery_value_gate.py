from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "delivery_value_gate.py"
SPEC = importlib.util.spec_from_file_location("fc_delivery_value_gate", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_delivery_value_gate"] = MODULE
SPEC.loader.exec_module(MODULE)
GateConfig = MODULE.GateConfig
evaluate_contract = MODULE.evaluate_contract


class DeliveryValueGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.history = Path(self.tmp.name) / "history.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _config(self) -> GateConfig:
        return GateConfig(role="dev", source="unit", history_path=self.history, burst_window_seconds=300, burst_threshold=3)

    def test_complete_with_full_evidence_passes(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=complete with proof; dev_artifact=apps/api/src/app.py; root_cause=bug_fix; fix_applied=patched handler; verify=before=500; after=200; test=pytest; tests_run=pytest:PASS; commit_sha=abcdef1; files_touched=apps/api/src/app.py; architecture_check=layer=api; imports_ok=yes; path_target=apps/api/src/app.py; vision_alignment=batch=BATCH-11; target=freshness; impact=restored; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=dev; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: DEV_DONE_1",
        ])
        result = evaluate_contract(payload, self._config(), now_epoch=1772800000)
        self.assertTrue(result.passed)
        self.assertIn("delivery_gate=pass", result.values["EVIDENCE"])

    def test_complete_without_commit_is_blocked(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=complete without commit; dev_artifact=apps/api/src/app.py; root_cause=bug_fix; fix_applied=patched handler; verify=before=500; after=200; test=pytest; tests_run=pytest:PASS; files_touched=apps/api/src/app.py; architecture_check=layer=api; imports_ok=yes; path_target=apps/api/src/app.py; vision_alignment=batch=BATCH-11; target=freshness; impact=restored; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=dev; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: DEV_DONE_2",
        ])
        result = evaluate_contract(payload, self._config(), now_epoch=1772800000)
        self.assertFalse(result.passed)
        self.assertIn("commit_sha", result.missing)
        self.assertEqual(result.values["BLOCKER_ID"], "DELIVERY_VALUE_INSUFFICIENT")

    def test_placeholders_are_blocked(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=complete placeholders; dev_artifact=?; root_cause=?; fix_applied=todo; verify=??; tests_run=SKIP(reason); commit_sha=abcdef1; files_touched=?; architecture_check=?; vision_alignment=?; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=dev; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: DEV_DONE_3",
        ])
        result = evaluate_contract(payload, self._config(), now_epoch=1772800000)
        self.assertFalse(result.passed)
        self.assertIn("artifact", result.missing)
        self.assertIn("verify", result.missing)

    def test_done_burst_inflation_detected(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=bad completion; dev_artifact=apps/api/src/app.py; root_cause=bug_fix; fix_applied=patched handler; verify=before=500; after=200; test=pytest; tests_run=pytest:PASS; files_touched=apps/api/src/app.py; architecture_check=layer=api; imports_ok=yes; path_target=apps/api/src/app.py; vision_alignment=batch=BATCH-11; target=freshness; impact=restored; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=dev; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: DEV_DONE_BURST",
        ])
        for idx in range(2):
            evaluate_contract(payload.replace("DEV_DONE_BURST", f"DEV_BURST_{idx}"), self._config(), now_epoch=1772800000 + idx)
        result = evaluate_contract(payload.replace("DEV_DONE_BURST", "DEV_BURST_3"), self._config(), now_epoch=1772800002)
        self.assertFalse(result.passed)
        self.assertTrue(result.inflation_detected)
        self.assertIn("delivery_signal_inflation_detected", result.values["EVIDENCE"])

    def test_planner_doc_only_autofills_files_and_architecture(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=planner closure with artifact only; planner_artifact=docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md; root_cause=dependency funnel; fix_applied=close analysis then claim next ready; verify=before=quality_fields_missing; after=quality_fields_backfilled; test=contract_guard_precheck; tests_run=SKIP(doc_only); cmd=SKIP(planner_doc_only); stream_id=BATCH-58; vision_alignment=batch=BATCH-58; target=planner_quality_backfill; impact=maintain_delivery_flow; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=planner; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: PLANNER_DONE_DOC_ONLY",
        ])
        cfg = GateConfig(role="planner", source="unit", history_path=self.history, burst_window_seconds=300, burst_threshold=3)
        result = evaluate_contract(payload, cfg, now_epoch=1772800000)
        self.assertTrue(result.passed)
        self.assertIn("files_touched=docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md", result.values["EVIDENCE"])
        self.assertIn("architecture_check=layer=platform", result.values["EVIDENCE"])

    def test_planner_doc_only_normalizes_path_style_architecture_and_verify(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=planner closure with split compound fields; planner_artifact=docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md; root_cause=dependency funnel; fix_applied=close analysis then claim next ready; verify=before=quality_fields_missing; test=python3 platform/automation/parallel_workstream.py context --role planner --limit 5; tests_run=NONE(planner_doc_only); cmd=SKIP(planner_doc_only); stream_id=BATCH-58; architecture_check=docs/architecture/ARCHITECTURE_MAP.md; architecture_plan_ref=docs/architecture/ARCHITECTURE_MAP.md; vision_alignment=batch=BATCH-unknown; target=data_ingestion_freshness_slo; impact=artefact_arch_pour_debloquer_DEV_01; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=planner; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: PLANNER_DONE_DOC_ONLY_SPLIT",
        ])
        cfg = GateConfig(role="planner", source="unit", history_path=self.history, burst_window_seconds=300, burst_threshold=3)
        result = evaluate_contract(payload, cfg, now_epoch=1772800000)
        self.assertTrue(result.passed)
        self.assertIn("architecture_check=layer=platform", result.values["EVIDENCE"])
        self.assertIn("path_target=docs/architecture/ARCHITECTURE_MAP.md", result.values["EVIDENCE"])
        self.assertIn("after=planner_delivery_gate_applied", result.values["EVIDENCE"])

    def test_planner_doc_only_detects_none_marker(self) -> None:
        payload = "\n".join([
            "STATUS: IN_PROGRESS",
            "DELTA: DONE",
            "EVIDENCE: task_update=complete; lock_check=ok; run_note=planner closure with NONE doc-only marker; planner_artifact=docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md; root_cause=dependency funnel; fix_applied=close analysis then claim next ready; verify=before=quality_fields_missing; test=python3 platform/automation/parallel_workstream.py context --role planner --limit 5; tests_run=NONE(planner_doc_only); commit_sha=NONE(doc_only); stream_id=BATCH-58; architecture_check=docs/architecture/ARCHITECTURE_MAP.md; architecture_plan_ref=docs/architecture/ARCHITECTURE_MAP.md; vision_alignment=batch=BATCH-unknown; target=data_ingestion_freshness_slo; impact=artefact_arch_pour_debloquer_DEV_01; issues=none; issue_count=0; issue_severity=none",
            "RISKS: none",
            "NEXT: owner=planner; action=done",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: PLANNER_DONE_DOC_ONLY_NONE",
        ])
        cfg = GateConfig(role="planner", source="unit", history_path=self.history, burst_window_seconds=300, burst_threshold=3)
        result = evaluate_contract(payload, cfg, now_epoch=1772800000)
        self.assertTrue(result.passed)
        self.assertIn("delivery_gate=pass", result.values["EVIDENCE"])


if __name__ == "__main__":
    unittest.main()
