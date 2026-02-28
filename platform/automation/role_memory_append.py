#!/usr/bin/env python3
"""Append compact role-contract memory lines with lock + trimming."""

from __future__ import annotations

import fcntl
import re
import sys
from pathlib import Path

CONTRACT_KEYS = {
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
}


def parse_contract(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        match = re.match(r"^\s*([A-Z_]+)\s*:\s*(.*)$", raw.strip())
        if not match:
            continue
        key = match.group(1).upper()
        if key in CONTRACT_KEYS and key not in values:
            values[key] = match.group(2).strip()
    return values


def parse_evidence_kv(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for fragment in raw.split(";"):
        if "=" not in fragment:
            continue
        key, value = fragment.split("=", 1)
        key_norm = key.strip().lower()
        if not key_norm or key_norm in out:
            continue
        out[key_norm] = re.sub(r"\s+", " ", value.strip())
    return out


def pick(evidence_kv: dict[str, str], key: str, default: str = "?") -> str:
    value = evidence_kv.get(key)
    if not value:
        return default
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) > 180:
        text = text[:180]
    return text


def build_line(role: str, source: str, ts_local: str, values: dict[str, str], evidence_kv: dict[str, str]) -> str:
    status = values.get("STATUS", "?")
    delta = values.get("DELTA", "?")
    verdict = values.get("VERDICT", "?")
    blocker = values.get("BLOCKER_ID", "NONE")
    next_action_unique = values.get("NEXT_ACTION_UNIQUE", "?")
    stream_id = pick(evidence_kv, "stream_id", "none")
    task_id = pick(evidence_kv, "task_id", "none")
    exec_report = pick(evidence_kv, "exec_report", "none")
    issues = pick(evidence_kv, "issues", "none")
    suggestions = pick(evidence_kv, "suggestions", "none")
    directive_id = pick(evidence_kv, "directive_id", "none")
    directive_ack = pick(evidence_kv, "directive_ack", "none")

    line = (
        f"- [{ts_local}] role={role} source={source} status={status} verdict={verdict} "
        f"delta={delta} blocker={blocker} stream_id={stream_id} task_id={task_id} "
        f"next_action_unique={next_action_unique} directive={directive_id}/{directive_ack} "
        f"exec_report={exec_report} issues={issues} suggestions={suggestions}"
    )
    return re.sub(r"\s+", " ", line).strip()


def ensure_header(mem_file: Path, role: str) -> None:
    if mem_file.exists():
        return
    mem_file.parent.mkdir(parents=True, exist_ok=True)
    mem_file.write_text(f"# {role}\n\n", encoding="utf-8")


def trim_if_needed(mem_file: Path) -> None:
    lines = mem_file.read_text(encoding="utf-8", errors="ignore").splitlines(True)
    if len(lines) <= 900:
        return
    head = lines[:40]
    tail = lines[-760:]
    mem_file.write_text("".join(head + ["\n"] + tail), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 7:
        print(
            "usage: role_memory_append.py <role> <source> <payload_file> <memory_file> <memory_lock_file> <ts_local>",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1]
    source = sys.argv[2]
    payload_file = Path(sys.argv[3])
    memory_file = Path(sys.argv[4])
    memory_lock_file = Path(sys.argv[5])
    ts_local = sys.argv[6]

    try:
        text = payload_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0

    values = parse_contract(text)
    evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))
    line = build_line(role, source, ts_local, values, evidence_kv)
    if not line:
        return 0

    memory_lock_file.parent.mkdir(parents=True, exist_ok=True)
    with memory_lock_file.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        ensure_header(memory_file, role)
        with memory_file.open("a", encoding="utf-8") as mem_fh:
            mem_fh.write(line + "\n")
        trim_if_needed(memory_file)
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
