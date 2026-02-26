#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

BLOCK_PATTERNS = [
    (r"curl\s+[^|\n]+\|\s*(bash|sh)", "remote script execution via curl pipe"),
    (r"wget\s+[^|\n]+\|\s*(bash|sh)", "remote script execution via wget pipe"),
    (r"\brm\s+-rf\s+/(\s|$)", "dangerous root wipe"),
    (r"\bmkfs\b|\bdd\s+if=", "disk-destructive command"),
    (r"\b(base64\s+(-d|--decode)|openssl\s+base64\s+-d)\b", "explicit base64 decode in command"),
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

MALICIOUS_IOC_PATTERNS = [
    (r"\b91\.92\.242\.30\b", "known malicious IOC IP detected"),
]

WORKSPACE = str(Path(__file__).resolve().parent.parent)

B64_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/=])([A-Za-z0-9+/]{40,}={0,2})(?![A-Za-z0-9+/=])")


@dataclass
class Decision:
    decision: str
    risk_score: int
    requires_confirmation: bool
    reasons: list[str]


def _decode_base64_candidates(text: str) -> list[str]:
    decoded_hits: list[str] = []
    for m in B64_TOKEN_RE.finditer(text):
        token = m.group(1)
        try:
            pad = "=" * ((4 - len(token) % 4) % 4)
            raw = base64.b64decode(token + pad, validate=True)
            s = raw.decode("utf-8", errors="ignore").strip()
            if s:
                decoded_hits.append(s)
        except (binascii.Error, ValueError):
            continue
    return decoded_hits


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

    for pat, reason in MALICIOUS_IOC_PATTERNS:
        if re.search(pat, low):
            reasons.append(f"BLOCK: {reason}")
            score += 80

    decoded_payloads = _decode_base64_candidates(cmd)
    for payload in decoded_payloads:
        p = payload.lower()
        if re.search(r"\b(curl|wget)\b", p) and re.search(r"\b(bash|sh)\b", p):
            reasons.append("BLOCK: decoded base64 payload contains remote shell execution pattern")
            score += 80
        elif re.search(r"https?://", p) and re.search(r"\b(bash|sh\s+-c)\b", p):
            reasons.append("BLOCK: decoded base64 payload contains URL + shell execution")
            score += 80
        elif re.search(r"https?://", p):
            reasons.append("CONFIRM: decoded base64 payload contains outbound URL")
            score += 20

        for pat, reason in MALICIOUS_IOC_PATTERNS:
            if re.search(pat, p):
                reasons.append(f"BLOCK: {reason} (found in decoded payload)")
                score += 80

    wd = str(Path(workdir).expanduser().resolve()) if workdir else WORKSPACE
    if wd != WORKSPACE and not wd.startswith(f"{WORKSPACE}/"):
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
