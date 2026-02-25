#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict

BLOCK_PATTERNS = [
    (r"curl\s+[^|\n]+\|\s*(bash|sh)", "remote script execution via curl pipe"),
    (r"wget\s+[^|\n]+\|\s*(bash|sh)", "remote script execution via wget pipe"),
    (r"\brm\s+-rf\s+/(\s|$)", "dangerous root wipe"),
    (r"\bmkfs\b|\bdd\s+if=", "disk-destructive command"),
]

CONFIRM_PATTERNS = [
    (r"\bsudo\b", "privilege escalation"),
    (r"\bsystemctl\b|\bservice\b", "service/system state change"),
    (r"\b(cron|crontab)\b", "persistence/scheduled task change"),
    (r"\brm\s+-rf\b", "recursive delete"),
    (r"\bcurl\b|\bwget\b", "outbound network call"),
    (r"\b(eval|bash\s+-c|sh\s+-c)\b", "injection-prone shell execution"),
    (r"\.env|~/.ssh|auth\.json|id_rsa|token|api[_-]?key", "possible secret exposure surface"),
]

WORKSPACE = "/home/venom/analyse-financiere"

@dataclass
class Decision:
    decision: str
    risk_score: int
    requires_confirmation: bool
    reasons: list[str]


def assess(cmd: str, workdir: str | None) -> Decision:
    low = cmd.lower()
    reasons: list[str] = []
    score = 0

    for pat, reason in BLOCK_PATTERNS:
        if re.search(pat, low):
            reasons.append(f"BLOCK: {reason}")
            score += 60

    for pat, reason in CONFIRM_PATTERNS:
        if re.search(pat, low):
            reasons.append(f"CONFIRM: {reason}")
            score += 15

    wd = workdir or WORKSPACE
    if not wd.startswith(WORKSPACE):
        reasons.append("CONFIRM: workdir outside approved workspace")
        score += 25

    if any(r.startswith("BLOCK:") for r in reasons):
        return Decision("BLOCK", min(score, 100), True, reasons)

    if any(r.startswith("CONFIRM:") for r in reasons):
        return Decision("CONFIRM", min(max(score, 20), 95), True, reasons)

    return Decision("ALLOW", 5, False, ["No high-risk patterns detected"])


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-exec command safety gate")
    ap.add_argument("--cmd", required=True, help="Command to evaluate")
    ap.add_argument("--workdir", default=WORKSPACE)
    args = ap.parse_args()

    d = assess(args.cmd, args.workdir)
    print(json.dumps(asdict(d), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
