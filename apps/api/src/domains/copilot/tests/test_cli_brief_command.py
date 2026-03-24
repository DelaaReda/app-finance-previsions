from __future__ import annotations

import subprocess
from pathlib import Path


def test_finance_copilot_brief_command_outputs_daily_brief():
    repo_root = Path(__file__).resolve().parents[6]

    result = subprocess.run(
        [str(repo_root / "finance-copilot.sh"), "brief"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    assert "BRIEF DU JOUR" in stdout
    assert "Sentiment:" in stdout
    assert len(stdout.strip()) > len("BRIEF DU JOUR\nSentiment:")
