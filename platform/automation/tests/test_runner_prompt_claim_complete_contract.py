#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "platform" / "automation" / "cron_tmux_role_runner.sh"


class RunnerPromptClaimCompleteContractTests(unittest.TestCase):
    def test_shared_prompt_separates_claim_handoff_from_complete(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn(
            "CLAIM/HANDOFF: publier ids + artifact + prochaine action concrete; pas de faux root_cause/fix_applied/verify uniquement pour satisfaire le contrat.",
            text,
        )
        self.assertIn(
            'COMPLETE: patch minimal, tests cibles, git add -A && git commit -m "<message>", puis complete/handoff avec preuve riche.',
            text,
        )

    def test_retry_prompt_only_requires_close_phase_fields_for_complete(self) -> None:
        text = RUNNER.read_text(encoding="utf-8", errors="ignore")
        self.assertIn(
            "EVIDENCE minimum: task_update + lock_check=ok + run_note (>=5 mots) + issues + issue_count + issue_severity + artifact_role.",
            text,
        )
        self.assertIn(
            "Si task_update=complete: ajouter root_cause + fix_applied + verify(before=/after=/test= ou proof=).",
            text,
        )
        self.assertIn(
            "Si task_update=claim|handoff: ajouter stream_id + task_id; ne pas inventer root_cause/fix_applied/verify pour satisfaire le contrat.",
            text,
        )
        self.assertNotIn(
            "artifact_rôle + root_cause + fix_applied + verify.",
            text,
        )


if __name__ == "__main__":
    unittest.main()
