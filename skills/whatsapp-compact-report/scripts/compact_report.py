#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def normalize(lines: list[str]) -> list[str]:
    out = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("```"):
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = line.replace("**", "*")
        line = re.sub(r"\s+", " ", line)
        out.append(line)
    return out


def classify(lines: list[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    done, blockers, nxt, evidence = [], [], [], []
    for line in lines:
        low = line.lower()
        if any(k in low for k in ["done", "completed", "ok", "fixed", "success"]):
            done.append(line)
        elif any(k in low for k in ["block", "error", "fail", "ko", "issue"]):
            blockers.append(line)
        elif any(k in low for k in ["next", "todo", "plan", "follow-up"]):
            nxt.append(line)
        elif any(k in line for k in ["/", ".py", ".sh", "http", "result_file="]):
            evidence.append(line)

    if not done and lines:
        done = lines[:2]
    if not evidence and lines:
        evidence = lines[-2:]
    return done[:3], blockers[:3], nxt[:3], evidence[:3]


def compose(done, blockers, nxt, evidence, max_chars: int) -> str:
    parts = ["*STATUS*", "*Done*:"]
    parts.extend([f"- {x}" for x in done] or ["- none"])
    parts.append("*Blockers*:")
    parts.extend([f"- {x}" for x in blockers] or ["- none"])
    parts.append("*Next*:")
    parts.extend([f"- {x}" for x in nxt] or ["- continue backlog"])
    parts.append("*Evidence*:")
    parts.extend([f"- {x}" for x in evidence] or ["- n/a"])

    msg = "\n".join(parts)
    if len(msg) <= max_chars:
        return msg

    for bucket in (evidence, nxt, blockers, done):
        while bucket and len(msg) > max_chars:
            bucket.pop()
            parts = ["*STATUS*", "*Done*:"]
            parts.extend([f"- {x}" for x in done] or ["- none"])
            parts.append("*Blockers*:")
            parts.extend([f"- {x}" for x in blockers] or ["- none"])
            parts.append("*Next*:")
            parts.extend([f"- {x}" for x in nxt] or ["- continue backlog"])
            parts.append("*Evidence*:")
            parts.extend([f"- {x}" for x in evidence] or ["- n/a"])
            msg = "\n".join(parts)

    if len(msg) > max_chars:
        msg = msg[: max_chars - 3].rstrip() + "..."
    return msg


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact WhatsApp-ready report")
    parser.add_argument("--input-file", help="Source text file (default: stdin)")
    parser.add_argument("--max-chars", type=int, default=950)
    args = parser.parse_args()

    if args.input_file:
        raw = Path(args.input_file).read_text(encoding="utf-8", errors="ignore")
    else:
        raw = sys.stdin.read()

    lines = normalize(raw.splitlines())
    done, blockers, nxt, evidence = classify(lines)
    print(compose(done, blockers, nxt, evidence, max_chars=args.max_chars))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
