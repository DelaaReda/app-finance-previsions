#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKSTREAM = ROOT / "scripts" / "parallel_workstream.py"
GOOD_CHANGE_PLAN = (
    "1 definir scope endpoint forecast ui; "
    "2 verifier dependencies et impact upstream downstream; "
    "3 analyser risk de regression forecast; "
    "4 executer verification tests pytest snapshot; "
    "5 preparer rollback fallback mitigation"
)
GOOD_ARCH_CHECKS = "forecast_contract; schema_stability; observability"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_command(board_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(WORKSTREAM), "--board", str(board_path), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _base_board(task_id: str = "BATCH-99-BACKEND") -> dict:
    return {
        "version": 1,
        "updated_at": utcnow(),
        "sprint": {"id": "S-TEST", "goal": "parallel prechange gate", "cadence_days": 14},
        "roles": {
            "backend_engineer": {"wip_limit": 3, "can_edit": True, "focus": "api and backend impl"},
            "dev": {"wip_limit": 2, "can_edit": True, "focus": "core execution"},
            "qa": {"wip_limit": 3, "can_edit": True, "focus": "quality"},
        },
        "streams": [
            {
                "id": "BATCH-99",
                "title": "BATCH-99",
                "priority": "P1",
                "source_state": "READY",
                "state": "READY",
                "created_at": utcnow(),
                "updated_at": utcnow(),
            }
        ],
        "tasks": [
            {
                "id": task_id,
                "stream_id": "BATCH-99",
                "code": "BACKEND",
                "title": "BATCH-99 [BACKEND]",
                "role": "backend_engineer",
                "state": "READY",
                "priority": "P1",
                "depends_on": [],
                "assignee": "",
                "blocked_reason": "",
                "artifacts": [],
                "notes": [],
                "handoff_to": "",
                "created_at": utcnow(),
                "updated_at": utcnow(),
                "started_at": "",
                "completed_at": "",
            }
        ],
        "handoffs": [],
        "events": [],
    }


class ParallelWorkstreamPrechangeGateTests(unittest.TestCase):
    def test_claim_requires_plan_and_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            board_path.write_text(json.dumps(_base_board(), ensure_ascii=True) + "\n", encoding="utf-8")

            cmd_missing = _run_command(
                board_path,
                ["claim", "--role", "backend_engineer", "--task", "BATCH-99-BACKEND"],
            )
            self.assertNotEqual(cmd_missing.returncode, 0, msg=cmd_missing.stderr)
            self.assertIn("PRECHANGE_PLAN_INVALID", cmd_missing.stderr + cmd_missing.stdout)

            cmd_bad_arch = _run_command(
                board_path,
                [
                    "claim",
                    "--role",
                    "backend_engineer",
                    "--task",
                    "BATCH-99-BACKEND",
                    "--change-plan",
                    GOOD_CHANGE_PLAN,
                    "--architecture-checks",
                    "API contract; observability",
                ],
            )
            self.assertNotEqual(cmd_bad_arch.returncode, 0, msg=cmd_bad_arch.stderr)
            self.assertIn("ARCHITECTURE_CHECK_INVALID", cmd_bad_arch.stderr + cmd_bad_arch.stdout)

            cmd_missing_reflection = _run_command(
                board_path,
                [
                    "claim",
                    "--role",
                    "backend_engineer",
                    "--task",
                    "BATCH-99-BACKEND",
                    "--change-plan",
                    "1 definir scope endpoint; 2 appliquer patch backend; 3 executer patch; 4 finaliser code; 5 documenter",
                    "--architecture-checks",
                    GOOD_ARCH_CHECKS,
                ],
            )
            self.assertNotEqual(cmd_missing_reflection.returncode, 0, msg=cmd_missing_reflection.stderr)
            self.assertIn("PRECHANGE_REFLECTION_INVALID", cmd_missing_reflection.stderr + cmd_missing_reflection.stdout)

            cmd_dup_plan = _run_command(
                board_path,
                [
                    "claim",
                    "--role",
                    "backend_engineer",
                    "--task",
                    "BATCH-99-BACKEND",
                    "--change-plan",
                    "1 inspecter code; 1 inspecter code; 1 inspecter code; 1 inspecter code; 1 inspecter code",
                    "--architecture-checks",
                    "forecast_contract; schema_stability; observability",
                ],
            )
            self.assertNotEqual(cmd_dup_plan.returncode, 0, msg=cmd_dup_plan.stderr)
            self.assertIn("PRECHANGE_PLAN_INVALID", cmd_dup_plan.stderr + cmd_dup_plan.stdout)

            cmd_ok = _run_command(
                board_path,
                [
                    "claim",
                    "--role",
                    "backend_engineer",
                    "--task",
                    "BATCH-99-BACKEND",
                    "--change-plan",
                    GOOD_CHANGE_PLAN,
                    "--architecture-checks",
                    GOOD_ARCH_CHECKS,
                ],
            )
            self.assertEqual(cmd_ok.returncode, 0, msg=cmd_ok.stderr)
            self.assertIn("CLAIM_OK", cmd_ok.stdout)

    def test_complete_accepts_claim_stored_preconditions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            board_path = Path(td) / "parallel-workstreams.json"
            proof_root = Path(td) / "proofs"
            board_path.write_text(json.dumps(_base_board("BATCH-99-BACKEND"), ensure_ascii=True) + "\n", encoding="utf-8")

            cmd_claim = _run_command(
                board_path,
                [
                    "claim",
                    "--role",
                    "backend_engineer",
                    "--task",
                    "BATCH-99-BACKEND",
                    "--change-plan",
                    GOOD_CHANGE_PLAN,
                    "--architecture-checks",
                    GOOD_ARCH_CHECKS,
                ],
            )
            self.assertEqual(cmd_claim.returncode, 0, msg=cmd_claim.stderr)
            self.assertIn("CLAIM_OK", cmd_claim.stdout)

            cmd_complete = _run_command(
                board_path,
                [
                    "complete",
                    "--role",
                    "backend_engineer",
                    "--task",
                    "BATCH-99-BACKEND",
                    "--artifact",
                    "copilot-app/backend/src/api/routes/judge.py",
                    "--note",
                    "ajout garde-fou prechange",
                    "--proof-root",
                    str(proof_root),
                    "--tests-run",
                    "SKIP(no_change)",
                ],
            )
            self.assertEqual(cmd_complete.returncode, 0, msg=cmd_complete.stderr)
            self.assertIn("COMPLETE_OK", cmd_complete.stdout)


if __name__ == "__main__":
    unittest.main()
