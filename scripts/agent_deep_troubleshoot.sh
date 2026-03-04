#!/usr/bin/env bash
# agent_deep_troubleshoot.sh — Deep troubleshooting snapshot per agent role
# Usage:
#   bash scripts/agent_deep_troubleshoot.sh
#   bash scripts/agent_deep_troubleshoot.sh dev
#   bash scripts/agent_deep_troubleshoot.sh planner dev admin
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

TICK_DIR="$ROOT/logs-codex-runs/fc-ticks"
LIVE_DIR="$ROOT/logs-codex-runs/role-runner"
ORCH_DIR="$ROOT/docs/operations/orchestrator"
if [[ ! -d "$ORCH_DIR" ]] && [[ -d "$ROOT/docs/orchestrator-ops" ]]; then
  ORCH_DIR="$ROOT/docs/orchestrator-ops"
fi
WORKBOARD_JSON="$ORCH_DIR/parallel-workstreams.json"
QUEUE_JSON="$ORCH_DIR/priority-queue.json"
GUARDIAN_EVENTS_JSONL="$ORCH_DIR/planner-guardian-events.jsonl"
GUARDIAN_LATEST_JSON="$ORCH_DIR/planner-guardian-latest.json"

DEFAULT_STATE_DIR="/home/venom/.openclaw/cron/role-state"
ALT_STATE_DIR="${HOME}/.openclaw/cron/role-state"
STATE_DIR_ENV="${FC_MONITOR_STATE_DIR:-${FC_STATE_DIR:-}}"
STATE_DIR="${ALT_STATE_DIR}"

pick_state_dir() {
  local best_dir=""
  local best_score=-1
  local candidate=""
  local score=0
  local contracts=0
  local runners=0
  local memories=0
  for candidate in "$STATE_DIR_ENV" "$DEFAULT_STATE_DIR" "$ALT_STATE_DIR"; do
    [[ -n "$candidate" ]] || continue
    [[ -d "$candidate" ]] || continue
    contracts="$(find "$candidate" -maxdepth 1 -type f -name '*.last_contract' 2>/dev/null | wc -l | tr -d ' ')"
    runners="$(find "$candidate" -maxdepth 1 -type f -name '*.run.lock' 2>/dev/null | wc -l | tr -d ' ')"
    memories="$(find "$candidate" -maxdepth 1 -type f -name '*.memory.lock' 2>/dev/null | wc -l | tr -d ' ')"
    score=$((contracts * 10 + runners * 3 + memories))
    if [[ "$score" -gt "$best_score" ]]; then
      best_score="$score"
      best_dir="$candidate"
    fi
  done
  if [[ -n "$best_dir" ]]; then
    STATE_DIR="$best_dir"
  fi
}
pick_state_dir

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

print_runner_health_summary() {
  local role="$1"
  local events="$LIVE_DIR/${role}.events.log"
  [[ -f "$events" ]] || { echo "  runner_health: no events log"; return 0; }

  python3 - "$events" <<'PY'
import re, sys
from collections import Counter
path = sys.argv[1]
engines = Counter()
fallback = 0
timeout_124 = 0
timeout_missing = 0
broken_pipe = 0
rate_limit_probe_error = 0

with open(path, "r", encoding="utf-8", errors="ignore") as fh:
    lines = fh.readlines()[-800:]

for ln in lines:
    m = re.search(r"event=startup detail=.*?\bagent=([a-zA-Z0-9_-]+)", ln)
    if m:
        engines[m.group(1).strip().lower()] += 1
    if "event=checkpoint_fallback" in ln:
        fallback += 1
        if "rc_primary=124" in ln or "rc_retry=124" in ln:
            timeout_124 += 1
        if "timeout: command not found" in ln:
            timeout_missing += 1
        if "Broken pipe" in ln:
            broken_pipe += 1
    if "event=rate_limit_probe_error" in ln:
        rate_limit_probe_error += 1

engine_list = ",".join(f"{k}:{v}" for k, v in sorted(engines.items())) if engines else "none"
if len(engines) > 1:
    print(f"  runner_health: MIXED_ENGINES engines={engine_list}")
else:
    print(f"  runner_health: engines={engine_list}")
print(
    "  runner_health: "
    f"fallback={fallback} timeout124={timeout_124} timeout_missing={timeout_missing} "
    f"broken_pipe={broken_pipe} rate_limit_probe_error={rate_limit_probe_error}"
)
PY
}

print_queue_schema_summary() {
  if [[ ! -f "$QUEUE_JSON" ]]; then
    echo "queue_schema: missing ($QUEUE_JSON)"
    return 0
  fi
  python3 - "$QUEUE_JSON" <<'PY'
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path, "r", encoding="utf-8", errors="ignore"))
except Exception as exc:
    print(f"queue_schema: invalid_json ({exc})")
    sys.exit(0)

items = data.get("items")
batches = data.get("batches")
items_n = len(items) if isinstance(items, list) else 0
batches_n = len(batches) if isinstance(batches, list) else 0
mode = "items" if isinstance(items, list) else ("batches" if isinstance(batches, list) else "unknown")
print(f"queue_schema: mode={mode} items={items_n} batches={batches_n}")
if mode != "items":
    print("queue_schema_alert: expected items[] canonical format")
PY
}

print_planner_guardian_summary() {
  [[ -f "$GUARDIAN_LATEST_JSON" ]] || { echo "planner_guardian: missing latest file"; return 0; }
  python3 - "$GUARDIAN_LATEST_JSON" "$GUARDIAN_EVENTS_JSONL" <<'PY'
import json, sys
latest_path, events_path = sys.argv[1], sys.argv[2]
latest = {}
try:
    latest = json.load(open(latest_path, "r", encoding="utf-8", errors="ignore"))
except Exception:
    latest = {}

if not isinstance(latest, dict):
    latest = {}
score = latest.get("score", "?")
level = latest.get("level", "?")
issues = latest.get("issues", [])
issues_text = ",".join(issues[:4]) if isinstance(issues, list) else "none"
summary = latest.get("summary", {}) if isinstance(latest.get("summary"), dict) else {}
task_update = summary.get("task_update", "?")
blocker = summary.get("blocker_id", "?")
print(f"planner_guardian: score={score} level={level} task_update={task_update} blocker={blocker}")
print(f"planner_guardian: issues={issues_text or 'none'}")

blocked = 0
handoff_missing = 0
batch_invalid = 0
none_no_signal = 0
ready_but_idle = 0
if events_path:
    try:
        with open(events_path, "r", encoding="utf-8", errors="ignore") as fh:
            events = [json.loads(ln) for ln in fh if ln.strip()]
    except Exception:
        events = []
    for ev in events[-120:]:
        if not isinstance(ev, dict):
            continue
        sm = ev.get("summary", {}) if isinstance(ev.get("summary"), dict) else {}
        if (sm.get("status") or "").upper() == "BLOCKED":
            blocked += 1
        blocker = (sm.get("blocker_id") or "").upper()
        if blocker == "HANDOFF_TO_MISSING":
            handoff_missing += 1
        if blocker == "PLANNER_BATCH_ID_INVALID":
            batch_invalid += 1
        if (sm.get("task_update") or "").lower() == "none_no_signal":
            none_no_signal += 1
        ev_issues = ev.get("issues", [])
        if isinstance(ev_issues, list) and "ready_but_none_task_update" in ev_issues:
            ready_but_idle += 1
print(
    "planner_guardian_recent: "
    f"blocked={blocked} handoff_missing={handoff_missing} batch_id_invalid={batch_invalid} "
    f"none_no_signal={none_no_signal} ready_but_none_task_update={ready_but_idle}"
)
PY
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

print_state_summary() {
  local contracts=0
  local run_locks=0
  local memory_locks=0
  if [[ -d "$STATE_DIR" ]]; then
    contracts="$(find "$STATE_DIR" -maxdepth 1 -type f -name '*.last_contract' 2>/dev/null | wc -l | tr -d ' ')"
    run_locks="$(find "$STATE_DIR" -maxdepth 1 -type f -name '*.run.lock' 2>/dev/null | wc -l | tr -d ' ')"
    memory_locks="$(find "$STATE_DIR" -maxdepth 1 -type f -name '*.memory.lock' 2>/dev/null | wc -l | tr -d ' ')"
  fi
  echo "state_dir_summary: contracts=${contracts} run_locks=${run_locks} memory_locks=${memory_locks}"
}

echo "Agent deep troubleshoot snapshot"
echo "workspace: $ROOT"
echo "state_dir: $STATE_DIR"
echo "orchestrator_dir: $ORCH_DIR"
print_state_summary
echo

print_queue_schema_summary
if [[ " ${ROLES[*]} " == *" planner "* ]]; then
  print_planner_guardian_summary
fi
echo

for role in "${ROLES[@]}"; do
  echo "=== role: $role ==="
  print_tick_summary "$role"
  print_live_summary "$role"
  print_runner_health_summary "$role"
  print_contract_summary "$role"
  print_proof_summary "$role"
  echo
done

echo "Hint:"
echo "  - detailed tick history: bash scripts/tick_history.sh <role> --n 20"
echo "  - monitor view: bash scripts/monitor_agents.sh"
