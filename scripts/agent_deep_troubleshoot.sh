#!/usr/bin/env bash
# agent_deep_troubleshoot.sh — Deep troubleshooting snapshot per agent role
# Usage:
#   bash scripts/agent_deep_troubleshoot.sh
#   bash scripts/agent_deep_troubleshoot.sh dev
#   bash scripts/agent_deep_troubleshoot.sh planner dev admin
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

TICK_DIR="$ROOT/logs-codex-runs/fc-ticks"
LIVE_DIR="$ROOT/logs-codex-runs/role-runner"
WORKBOARD_JSON="$ROOT/docs/operations/orchestrator/parallel-workstreams.json"

DEFAULT_STATE_DIR="/home/venom/.openclaw/cron/role-state"
ALT_STATE_DIR="${HOME}/.openclaw/cron/role-state"
if [[ -d "$DEFAULT_STATE_DIR" ]]; then
  STATE_DIR="$DEFAULT_STATE_DIR"
else
  STATE_DIR="$ALT_STATE_DIR"
fi

if [[ "$#" -gt 0 ]]; then
  ROLES=("$@")
else
  ROLES=(planner dev admin)
fi

print_tick_summary() {
  local role="$1"
  local log="$TICK_DIR/${role}.tick.log"
  [[ -f "$log" ]] || { echo "  tick_log: missing ($log)"; return 0; }

  echo "  tick_log: $log"
  echo "  recent_ticks:"
  grep -E '\[END\]|\[SKIP\]|\[BACKOFF\]' "$log" | tail -n 6 | sed 's/^/    /' || echo "    (no recent tick markers)"

  local nonzero_24h
  nonzero_24h="$(python3 - "$log" <<'PY'
import re, sys, time
from datetime import datetime
path = sys.argv[1]
now = int(time.time())
cutoff = now - 24*3600
count = 0
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}).*?\[END\].*?rc=(\d+)', line)
        if not m:
            continue
        ts = int(datetime.fromisoformat(m.group(1)).timestamp())
        if ts < cutoff:
            continue
        if int(m.group(2)) != 0:
            count += 1
print(count)
PY
)"
  echo "  failures_last_24h: ${nonzero_24h}"
}

print_live_summary() {
  local role="$1"
  local live="$LIVE_DIR/${role}.live.log"
  [[ -f "$live" ]] || { echo "  live_log: missing ($live)"; return 0; }
  echo "  live_log: $live"
  echo "  runner_signals:"
  grep -E 'primary_prompt_end|retry_prompt_begin|checkpoint_fallback|contract_guard_unavailable|final_output source=' "$live" | tail -n 8 | sed 's/^/    /' || echo "    (no runner signal markers)"
}

print_contract_summary() {
  local role="$1"
  local cfile="$STATE_DIR/${role}.last_contract"
  [[ -f "$cfile" ]] || { echo "  last_contract: missing ($cfile)"; return 0; }

  local status verdict blocker next evidence
  status="$(sed -n 's/^STATUS:[[:space:]]*//p' "$cfile" | head -1)"
  verdict="$(sed -n 's/^VERDICT:[[:space:]]*//p' "$cfile" | head -1)"
  blocker="$(sed -n 's/^BLOCKER_ID:[[:space:]]*//p' "$cfile" | head -1)"
  next="$(sed -n 's/^NEXT_ACTION_UNIQUE:[[:space:]]*//p' "$cfile" | head -1)"
  evidence="$(sed -n 's/^EVIDENCE:[[:space:]]*//p' "$cfile" | head -1)"

  echo "  last_contract: $cfile"
  echo "    status=${status:-?} verdict=${verdict:-?} blocker=${blocker:-NONE}"
  echo "    next_action=${next:-?}"
  if [[ -n "$evidence" ]]; then
    local task_update run_note root_cause fix_applied verify reuse_check
    task_update="$(printf '%s\n' "$evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*task_update=//p' | head -1)"
    run_note="$(printf '%s\n' "$evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*run_note=//p' | head -1)"
    root_cause="$(printf '%s\n' "$evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*root_cause=//p' | head -1)"
    fix_applied="$(printf '%s\n' "$evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*fix_applied=//p' | head -1)"
    verify="$(printf '%s\n' "$evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*verify=//p' | head -1)"
    reuse_check="$(printf '%s\n' "$evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*reuse_check=//p' | head -1)"
    echo "    evidence: task_update=${task_update:-?} run_note=$(printf '%s' "${run_note:-?}" | cut -c1-80)"
    [[ -n "$root_cause" ]] && echo "    evidence: root_cause=$(printf '%s' "$root_cause" | cut -c1-90)"
    [[ -n "$fix_applied" ]] && echo "    evidence: fix_applied=$(printf '%s' "$fix_applied" | cut -c1-90)"
    [[ -n "$verify" ]] && echo "    evidence: verify=$(printf '%s' "$verify" | cut -c1-90)"
    [[ -n "$reuse_check" ]] && echo "    evidence: reuse_check=$(printf '%s' "$reuse_check" | cut -c1-80)"
  fi
}

latest_proof_for_role() {
  local role="$1"
  if [[ ! -f "$WORKBOARD_JSON" ]]; then
    printf '\n'
    return 0
  fi
  python3 - "$WORKBOARD_JSON" "$role" <<'PY'
import json, sys
path, role = sys.argv[1], sys.argv[2]
proof = ""
try:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict):
        events = d.get("events", [])
        if isinstance(events, list):
            for e in reversed(events):
                if not isinstance(e, dict):
                    continue
                if e.get("kind") != "complete":
                    continue
                det = e.get("details", {})
                if not isinstance(det, dict):
                    continue
                if str(det.get("role", "")).strip() != role:
                    continue
                pm = str(det.get("proof_manifest", "")).strip()
                if pm:
                    proof = pm
                    break
except Exception:
    pass
print(proof)
PY
}

print_proof_summary() {
  local role="$1"
  local proof_rel
  proof_rel="$(latest_proof_for_role "$role" || true)"
  if [[ -z "$proof_rel" ]]; then
    echo "  latest_proof: none for role=$role"
    return 0
  fi
  local proof="$ROOT/$proof_rel"
  if [[ ! -f "$proof" ]]; then
    echo "  latest_proof: missing file ($proof_rel)"
    return 0
  fi
  echo "  latest_proof: $proof_rel"
  sed -n 's/^produced_at_utc:[[:space:]]*//p' "$proof" | head -1 | sed 's/^/    produced_at_utc=/'
  sed -n 's/^  note:[[:space:]]*//p' "$proof" | head -1 | sed 's/^/    note=/'
  sed -n 's/^      result:[[:space:]]*//p' "$proof" | head -1 | sed 's/^/    test_result=/'
  sed -n 's/^    - cmd:[[:space:]]*//p' "$proof" | head -1 | cut -c1-180 | sed 's/^/    first_cmd=/'
}

echo "Agent deep troubleshoot snapshot"
echo "workspace: $ROOT"
echo "state_dir: $STATE_DIR"
echo

for role in "${ROLES[@]}"; do
  echo "=== role: $role ==="
  print_tick_summary "$role"
  print_live_summary "$role"
  print_contract_summary "$role"
  print_proof_summary "$role"
  echo
done

echo "Hint:"
echo "  - detailed tick history: bash scripts/tick_history.sh <role> --n 20"
echo "  - monitor view: bash scripts/monitor_agents.sh"
