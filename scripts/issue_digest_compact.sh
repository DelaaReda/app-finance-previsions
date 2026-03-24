#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
ORCH_DIR="${ROOT}/logs-codex-runs/orchestrator-state"
if [[ ! -d "$ORCH_DIR" ]]; then
  ORCH_DIR="${ROOT}/docs/operations/orchestrator"
fi

WINDOW_MIN="${1:-60}"
if ! [[ "$WINDOW_MIN" =~ ^[0-9]+$ ]]; then
  WINDOW_MIN=60
fi

LATEST_FILE="${TMUX_ROLE_ITERATION_ISSUES_LATEST_FILE:-${ORCH_DIR}/agent-iteration-issues-latest.json}"
EVENTS_FILE="${TMUX_ROLE_ITERATION_ISSUES_EVENTS_FILE:-${ORCH_DIR}/agent-iteration-issues.jsonl}"

python3 - "$WINDOW_MIN" "$LATEST_FILE" "$EVENTS_FILE" <<'PY'
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

window_min = max(1, int(sys.argv[1]))
latest_path = Path(sys.argv[2])
events_path = Path(sys.argv[3])
roles = ["planner", "dev", "admin"]
order = {"INFO": 0, "WARN": 1, "ERROR": 2, "CRITICAL": 3}


def parse_ts(raw: str) -> datetime | None:
    txt = str(raw or "").strip()
    if not txt:
        return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(txt)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def one_line(value: str, limit: int = 40) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


now = datetime.now(timezone.utc)
cutoff = now - timedelta(minutes=window_min)

records: list[dict] = []
if events_path.exists():
    for ln in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not ln.strip():
            continue
        try:
            item = json.loads(ln)
        except Exception:
            continue
        if not isinstance(item, dict):
            continue
        ts = parse_ts(item.get("ts_utc", ""))
        if ts is None or ts < cutoff:
            continue
        records.append(item)

severity_totals = Counter()
role_latest: dict[str, dict] = {}
role_issue_counts = Counter()
critical = 0

for rec in records:
    role = str(rec.get("role", ""))
    if role not in roles:
        continue
    ts = parse_ts(rec.get("ts_utc", ""))
    if ts is None:
        continue
    old = role_latest.get(role)
    if old is None or parse_ts(old.get("ts_utc", "")) is None or parse_ts(old.get("ts_utc", "")) < ts:
        role_latest[role] = rec
    if rec.get("issue_status") != "has_issues":
        continue
    role_issue_counts[role] += int(rec.get("issue_count") or 0)
    max_sev = str(rec.get("max_severity", "INFO")).upper()
    severity_totals[max_sev] += 1
    if max_sev == "CRITICAL":
        critical += 1

if latest_path.exists():
    try:
        latest = json.loads(latest_path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(latest, dict):
            role_data = latest.get("roles", {})
            if isinstance(role_data, dict):
                for role in roles:
                    item = role_data.get(role)
                    if isinstance(item, dict) and role not in role_latest:
                        role_latest[role] = item
    except Exception:
        pass

line1 = (
    f"window={window_min}m total={len(records)} "
    f"warn={severity_totals.get('WARN',0)} error={severity_totals.get('ERROR',0)} critical={critical}"
)

lines = [line1]
for role in roles:
    rec = role_latest.get(role, {})
    max_sev = str(rec.get("max_severity", "INFO")).upper()
    age_txt = "na"
    ts = parse_ts(rec.get("ts_utc", ""))
    if ts is not None:
        age_txt = f"{max(0, int((now - ts).total_seconds() // 60))}m"
    issues = rec.get("issues", [])
    code = "none"
    if isinstance(issues, list) and issues:
        first = issues[0]
        if isinstance(first, dict):
            code = str(first.get("code", "none")) or "none"
    line = f"{role} issues_60m={role_issue_counts.get(role,0)} last={one_line(code)} sev={max_sev} age={age_txt}"
    lines.append(line)

if critical > 0:
    next_action = "next=stabilize_critical_roles"
elif severity_totals.get("ERROR", 0) > 0:
    next_action = "next=fix_recent_error_codes"
elif len(records) == 0 or sum(severity_totals.values()) == 0:
    next_action = "next=none"
else:
    next_action = "next=monitor_and_prevent_repeat"
lines.append(next_action)

for ln in lines[:5]:
    print(one_line(ln, 120))
PY
