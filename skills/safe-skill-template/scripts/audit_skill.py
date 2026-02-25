#!/usr/bin/env python3
"""
Lightweight static audit for OpenClaw/Codex skills.

Usage:
  python3 audit_skill.py --skill-dir /path/to/skill
  python3 audit_skill.py --skill-dir /path/to/skill --json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


@dataclass
class Finding:
    severity: str
    category: str
    file: str
    line: int
    message: str
    snippet: str


CHECKS = [
    (
        "HIGH",
        "dangerous_shell",
        re.compile(r"(curl\s+[^|]+?\|\s*(bash|sh))|(wget\s+[^|]+?\|\s*(bash|sh))", re.IGNORECASE),
        "Potential remote shell execution pattern.",
    ),
    (
        "HIGH",
        "hardcoded_secret",
        re.compile(
            r"(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
            re.IGNORECASE,
        ),
        "Potential hardcoded secret.",
    ),
    (
        "HIGH",
        "hardcoded_target",
        re.compile(
            r"(\+\d{8,15})|((target|chat_id|recipient|to)\s*[:=]\s*['\"]?\+?\d{6,15}['\"]?)|(os\.environ\.get\(\s*['\"][A-Z0-9_]*(TARGET|CHAT_ID|RECIPIENT|TO)[A-Z0-9_]*['\"]\s*,\s*['\"]\+?\d{6,15}['\"]\s*\))",
            re.IGNORECASE,
        ),
        "Potential hardcoded recipient/target id.",
    ),
    (
        "MEDIUM",
        "outbound_messaging",
        re.compile(
            r"(channel\s*[:=]\s*['\"]?(telegram|whatsapp|slack|discord)['\"]?)|(message\s*send)",
            re.IGNORECASE,
        ),
        "Outbound messaging behavior detected; verify explicit user approval flow.",
    ),
    (
        "MEDIUM",
        "external_url",
        re.compile(r"https?://[^\s\"')]+", re.IGNORECASE),
        "External URL reference detected; verify domain allowlist and necessity.",
    ),
    (
        "LOW",
        "destructive_delete",
        re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
        "Destructive delete command detected.",
    ),
]


def iter_text_files(skill_dir: Path) -> Iterable[Path]:
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"SKILL.md", "HOOK.md"}:
            yield path


def scan_file(path: Path, root: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    lines = raw.splitlines()
    for idx, line in enumerate(lines, start=1):
        for severity, category, pattern, message in CHECKS:
            match = pattern.search(line)
            if not match:
                continue

            # Reduce noise: allow localhost URLs by default.
            if category == "external_url":
                url = match.group(0)
                if "127.0.0.1" in url or "localhost" in url:
                    continue

            # Reduce noise: markdown policy text often references risky commands as examples.
            if category == "destructive_delete" and path.suffix.lower() in {".md", ".txt"}:
                continue

            findings.append(
                Finding(
                    severity=severity,
                    category=category,
                    file=str(path.relative_to(root)),
                    line=idx,
                    message=message,
                    snippet=line.strip()[:220],
                )
            )
    return findings


def summarize(findings: List[Finding]) -> dict:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in findings:
        counts[item.severity] = counts.get(item.severity, 0) + 1
    if counts["HIGH"] > 0:
        verdict = "BLOCK"
    elif counts["MEDIUM"] > 0:
        verdict = "REVIEW"
    else:
        verdict = "ALLOW"
    return {"counts": counts, "verdict": verdict}


def main() -> int:
    parser = argparse.ArgumentParser(description="Static security scan for a skill directory.")
    parser.add_argument("--skill-dir", required=True, help="Path to skill folder.")
    parser.add_argument("--json", action="store_true", help="Output JSON.")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).expanduser().resolve()
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise SystemExit(f"Skill directory not found: {skill_dir}")

    findings: List[Finding] = []
    for file_path in iter_text_files(skill_dir):
        findings.extend(scan_file(file_path, skill_dir))

    summary = summarize(findings)

    if args.json:
        payload = {
            "skill_dir": str(skill_dir),
            "summary": summary,
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Skill dir: {skill_dir}")
    print(f"Verdict : {summary['verdict']}")
    print(
        "Counts  : HIGH={HIGH} MEDIUM={MEDIUM} LOW={LOW}".format(
            HIGH=summary["counts"]["HIGH"],
            MEDIUM=summary["counts"]["MEDIUM"],
            LOW=summary["counts"]["LOW"],
        )
    )
    print("")

    for finding in findings:
        print(
            "[{sev}] {cat} {file}:{line} - {msg}\n  {snip}".format(
                sev=finding.severity,
                cat=finding.category,
                file=finding.file,
                line=finding.line,
                msg=finding.message,
                snip=finding.snippet,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
