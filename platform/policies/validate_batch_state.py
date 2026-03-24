#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from orchestrator_paths import resolve_orchestrator_read_path

VALID = {
    "READY",
    "IN_SPRINT",
    "RUNNING",
    "QA_REVIEW",
    "PASS",
    "BLOCKED",
    "CLOSED",
}
ALLOWED_TRANSITIONS = {
    "READY": {"IN_SPRINT", "RUNNING", "BLOCKED"},
    "IN_SPRINT": {"RUNNING", "BLOCKED"},
    "RUNNING": {"QA_REVIEW", "BLOCKED"},
    "QA_REVIEW": {"PASS", "BLOCKED"},
    "PASS": {"CLOSED"},
    "BLOCKED": {"READY", "IN_SPRINT", "RUNNING", "CLOSED"},
    "CLOSED": set(),
}
DEFAULT_QUEUE_FILE = Path("logs-codex-runs/orchestrator-state/priority-queue.json")


def resolve_queue_path(raw: str) -> Path:
    path = Path(raw)
    if path.exists():
        return path
    if str(raw).strip() == str(DEFAULT_QUEUE_FILE):
        return resolve_orchestrator_read_path(ROOT, "priority-queue.json")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_QUEUE_FILE))
    args = ap.parse_args()

    p = resolve_queue_path(args.file)
    if not p.exists():
        print(f"BLOCKED: missing file {p}")
        return 2

    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.get("items", [])
    ids = {i.get("id") for i in items}
    errs: list[str] = []

    for it in items:
        bid = it.get("id")
        state = it.get("state")
        if state not in VALID:
            errs.append(f"{bid}: invalid state {state}")
        deps = it.get("depends_on", []) or []
        for dep_id in deps:
            if dep_id not in ids:
                errs.append(f"{bid}: unknown dependency {dep_id}")

    for it in items:
        bid = it.get("id")
        state = it.get("state")
        deps = it.get("depends_on", []) or []
        if state in {"IN_SPRINT", "RUNNING", "QA_REVIEW", "PASS", "CLOSED"}:
            for dep_id in deps:
                dep = next((x for x in items if x.get("id") == dep_id), None)
                if dep and dep.get("state") not in {"PASS", "CLOSED"}:
                    errs.append(f"{bid}: dependency {dep_id} not PASS/CLOSED")

    if errs:
        print("VERDICT: BLOCKED")
        for err in errs:
            print(f"- {err}")
        return 1

    print("VERDICT: PASS")
    print(f"validated_items={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
