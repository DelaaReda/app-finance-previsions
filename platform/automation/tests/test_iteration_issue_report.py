#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "iteration_issue_report.py"


def _payload(evidence: str = "issues=none; task_update=none_no_signal") -> str:
    return "\n".join(
        [
            "STATUS: IN_PROGRESS",
            "DELTA: NO_DELTA",
            f"EVIDENCE: {evidence}",
            "RISKS: none",
            "NEXT: continue",
            "VERDICT: GO_WITH_CAUTION",
            "BLOCKER_ID: NONE",
            "NEXT_ACTION_UNIQUE: TEST_NEXT",
        ]
    )


class IterationIssueReportTests(unittest.TestCase):
    def _run_report(
        self,
        *,
        tmp: Path,
        role: str,
        source: str,
        tick_id: str,
        contract_text: str,
        rc_primary: int,
        rc_retry: int,
        rc_final: int,
        rc_codex: int,
        raw_primary: str = "",
        raw_retry: str = "",
        raw_codex: str = "",
        trace: str = "",
    ) -> dict:
        payload_file = tmp / f"{tick_id}.payload.txt"
        latest_file = tmp / "agent-iteration-issues-latest.json"
        events_file = tmp / "agent-iteration-issues.jsonl"
        state_dir = tmp / "state"
        raw_primary_file = tmp / f"{tick_id}.raw.primary.txt"
        raw_retry_file = tmp / f"{tick_id}.raw.retry.txt"
        raw_codex_file = tmp / f"{tick_id}.raw.codex.txt"
        trace_file = tmp / f"{tick_id}.trace.log"

        payload_file.write_text(contract_text, encoding="utf-8")
        raw_primary_file.write_text(raw_primary, encoding="utf-8")
        raw_retry_file.write_text(raw_retry, encoding="utf-8")
        raw_codex_file.write_text(raw_codex, encoding="utf-8")
        trace_file.write_text(trace, encoding="utf-8")

        cmd = [
            sys.executable,
            str(SCRIPT),
            role,
            source,
            str(payload_file),
            str(latest_file),
            str(events_file),
            str(state_dir),
            tick_id,
            "codex",
            "tmux",
            str(rc_primary),
            str(rc_retry),
            str(rc_final),
            str(rc_codex),
            str(raw_primary_file),
            str(raw_retry_file),
            str(raw_codex_file),
            str(trace_file),
            "queue_v1",
            "workboard_v1",
        ]
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, msg=run.stderr)

        latest = json.loads(latest_file.read_text(encoding="utf-8"))
        self.assertIn("roles", latest)
        self.assertIn(role, latest["roles"])
        return latest["roles"][role]

    def test_forces_has_issues_when_rc_non_zero_even_if_contract_says_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            record = self._run_report(
                tmp=Path(td),
                role="admin",
                source="primary_structured",
                tick_id="T1",
                contract_text=_payload("issues=none; task_update=none_no_signal"),
                rc_primary=1,
                rc_retry=0,
                rc_final=1,
                rc_codex=-1,
                raw_primary="operation not permitted while creating directory",
            )
            self.assertEqual(record["issue_status"], "has_issues")
            self.assertGreater(record["issue_count"], 0)
            codes = [x.get("code") for x in record.get("issues", []) if isinstance(x, dict)]
            self.assertIn("PERMISSION_OP_NOT_PERMITTED", codes)

    def test_maps_expected_codes_from_rc_and_signatures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            record = self._run_report(
                tmp=Path(td),
                role="planner",
                source="fallback_checkpoint",
                tick_id="T2",
                contract_text=_payload("issues=signal_unparseable; fallback_mode=checkpoint"),
                rc_primary=43,
                rc_retry=124,
                rc_final=124,
                rc_codex=65,
                raw_primary="session_not_ready role=planner",
                raw_retry="printf: write error: Broken pipe",
                trace="rate_limit_probe_error bin=codex rc=1",
            )
            codes = {x.get("code") for x in record.get("issues", []) if isinstance(x, dict)}
            self.assertIn("TIMEOUT_124", codes)
            self.assertIn("SESSION_NOT_READY_43", codes)
            self.assertIn("BROKEN_PIPE", codes)
            self.assertIn("CHECKPOINT_FALLBACK", codes)
            self.assertIn("RATE_LIMIT_PROBE_ERROR", codes)
            self.assertIn("CONTRACT_PARSE_FAILED", codes)
            self.assertEqual(record["issue_status"], "has_issues")
            self.assertEqual(record["max_severity"], "ERROR")

    def test_escalates_to_critical_after_repeated_same_code(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            base_payload = _payload("issues=none; task_update=none_no_signal")
            self._run_report(
                tmp=tmp,
                role="dev",
                source="retry_structured",
                tick_id="T3A",
                contract_text=base_payload,
                rc_primary=124,
                rc_retry=124,
                rc_final=124,
                rc_codex=-1,
                raw_primary="timeout reached",
            )
            self._run_report(
                tmp=tmp,
                role="dev",
                source="retry_structured",
                tick_id="T3B",
                contract_text=base_payload,
                rc_primary=124,
                rc_retry=124,
                rc_final=124,
                rc_codex=-1,
                raw_primary="timeout reached",
            )
            third = self._run_report(
                tmp=tmp,
                role="dev",
                source="retry_structured",
                tick_id="T3C",
                contract_text=base_payload,
                rc_primary=124,
                rc_retry=124,
                rc_final=124,
                rc_codex=-1,
                raw_primary="timeout reached",
            )
            timeout_issue = [
                i for i in third.get("issues", [])
                if isinstance(i, dict) and i.get("code") == "TIMEOUT_124"
            ]
            self.assertTrue(timeout_issue)
            self.assertEqual(timeout_issue[0].get("severity"), "CRITICAL")
            self.assertEqual(third["max_severity"], "CRITICAL")

    def test_does_not_flag_timeout_on_budget_strings_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            record = self._run_report(
                tmp=Path(td),
                role="planner",
                source="primary_structured",
                tick_id="T4",
                contract_text=_payload("issues=none; task_update=none_no_ready"),
                rc_primary=0,
                rc_retry=0,
                rc_final=0,
                rc_codex=0,
                raw_primary="dispatch_prompt timeout_budget=300s retry_timeout_budget=120s",
                trace="event=primary_prompt_begin detail=tick=T4 timeout=300s channel=codex_exec",
            )
            self.assertEqual(record["issue_status"], "none")
            self.assertEqual(record["issue_count"], 0)

    def test_rate_limit_probe_error_does_not_escalate_to_critical_on_repeats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            base_payload = _payload("issues=none; task_update=none_no_signal")
            for tick_id in ("RL1", "RL2", "RL3"):
                record = self._run_report(
                    tmp=tmp,
                    role="planner",
                    source="rate_limit_gate_probe",
                    tick_id=tick_id,
                    contract_text=base_payload.replace("IN_PROGRESS", "RATE_LIMIT_SKIP", 1).replace("NO_DELTA", "RATE_LIMIT_BACKOFF", 1),
                    rc_primary=1,
                    rc_retry=0,
                    rc_final=0,
                    rc_codex=-1,
                    raw_primary="{\"type\":\"error\",\"message\":\"You've hit your usage limit.\"}",
                )

            rate_limit_issue = [
                i for i in record.get("issues", [])
                if isinstance(i, dict) and i.get("code") == "RATE_LIMIT_PROBE_ERROR"
            ]
            self.assertTrue(rate_limit_issue)
            self.assertEqual(rate_limit_issue[0].get("severity"), "WARN")
            self.assertEqual(record["max_severity"], "WARN")


if __name__ == "__main__":
    unittest.main()
