#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="docs/orchestrator-ops/priority-queue.json")
    args = ap.parse_args()

    p = Path(args.file)
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
      for d in deps:
          if d not in ids:
              errs.append(f"{bid}: unknown dependency {d}")

    for it in items:
      bid = it.get("id")
      state = it.get("state")
      deps = it.get("depends_on", []) or []
      if state in {"IN_SPRINT", "RUNNING", "QA_REVIEW", "PASS", "CLOSED"}:
          for d in deps:
              dep = next((x for x in items if x.get("id") == d), None)
              if dep and dep.get("state") not in {"PASS", "CLOSED"}:
                  errs.append(f"{bid}: dependency {d} not PASS/CLOSED")

    if errs:
      print("VERDICT: BLOCKED")
      for e in errs:
        print(f"- {e}")
      return 1

    print("VERDICT: PASS")
    print(f"validated_items={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
