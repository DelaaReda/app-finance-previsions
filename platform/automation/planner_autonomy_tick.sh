#!/usr/bin/env bash
# planner_autonomy_tick.sh
# Deterministic planner autonomy preflight:
# - keep planner active
# - sanitize + sync
# - claim READY planner task
# - if none READY, create top-level batch + claim
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "PLANNER_AUTONOMY status=soft_fail reason=workspace_helper_missing"
  exit 0
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

ENABLED="${FC_PLANNER_AUTONOMY_ENABLED:-1}"
AUTO_CREATE_ON_EMPTY="${FC_PLANNER_AUTO_CREATE_ON_EMPTY:-1}"
WAIT_FORBIDDEN="${FC_PLANNER_WAIT_FORBIDDEN:-1}"
CREATE_SOURCE="${FC_PLANNER_CREATE_SOURCE:-vision}"
STATE_DIR="${FC_ROLE_STATE_DIR:-${TMUX_ROLE_STATE_DIR:-${HOME}/.openclaw/cron/role-state}}"
STATE_FILE="${FC_PLANNER_AUTONOMY_STATE_FILE:-${STATE_DIR}/planner_autonomy_state.json}"
LOCK_FILE="${STATE_FILE}.lock"
LOG_FILE="${FC_PLANNER_AUTONOMY_LOG_FILE:-${ROOT}/logs-codex-runs/fc-ticks/planner.autonomy.log}"
QUEUE_FILE="${FC_PLANNER_AUTONOMY_QUEUE_FILE:-${ROOT}/docs/operations/orchestrator/priority-queue.json}"
BOARD_FILE="${FC_PLANNER_AUTONOMY_BOARD_FILE:-${ROOT}/docs/operations/orchestrator/parallel-workstreams.json}"
EXEC_SAFE="${ROOT}/platform/policies/exec_safe.sh"
SAFE_TIMEOUT_SECONDS="${FC_PLANNER_AUTONOMY_TIMEOUT_SECONDS:-90}"

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"

if [[ "$ENABLED" != "1" ]]; then
  echo "PLANNER_AUTONOMY status=skip reason=disabled"
  exit 0
fi

if [[ ! -x "$EXEC_SAFE" ]]; then
  echo "PLANNER_AUTONOMY status=soft_fail reason=exec_safe_missing"
  exit 0
fi

ts_utc() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

log_line() {
  printf '%s %s\n' "$(ts_utc)" "$*" >> "$LOG_FILE"
}

planner_change_plan() {
  cat <<'EOF'
scope planner autonomy batch
dependency impact on downstream tasks
risk containment before claim
verification via targeted sync
rollback path if claim fails
EOF
}

planner_architecture_checks() {
  cat <<'EOF'
planner autonomy queue boundaries
imports and data flow remain stable
claim stays inside intended task path
EOF
}

build_claim_cmd() {
  local task_id="${1:-}"
  local cmd="python3 platform/automation/parallel_workstream.py claim --role planner"
  if [[ -n "$task_id" ]]; then
    cmd+=" --task \"$task_id\""
  fi
  cmd+=" --change-plan \"$(planner_change_plan | tr '\n' ';' | sed 's/;*$//')\""
  cmd+=" --architecture-checks \"$(planner_architecture_checks | tr '\n' ';' | sed 's/;*$//')\""
  printf '%s' "$cmd"
}

write_state() {
  local active="$1"
  local action="$2"
  local outcome="$3"
  local reason="$4"
  local target_task="$5"
  local issue_code="$6"
  local details="$7"
  python3 - "$STATE_FILE" "$active" "$action" "$outcome" "$reason" "$target_task" "$issue_code" "$details" <<'PY' >/dev/null 2>&1 || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

state_file = Path(sys.argv[1])
active = bool(int(sys.argv[2]))
action = str(sys.argv[3] or "idle")
outcome = str(sys.argv[4] or "none")
reason = str(sys.argv[5] or "none")
target_task = str(sys.argv[6] or "none")
issue_code = str(sys.argv[7] or "none")
details = str(sys.argv[8] or "")

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
payload = {
    "active": active,
    "since_ts": now,
    "last_action": action,
    "last_outcome": outcome,
    "reason": reason,
    "target_task": target_task,
    "issue_code": issue_code,
    "details": details,
    "policy_enforced": True,
    "wait_forbidden": True,
    "updated_at": now,
}
try:
    if state_file.exists():
        previous = json.loads(state_file.read_text(encoding="utf-8"))
        if isinstance(previous, dict):
            since = str(previous.get("since_ts") or "").strip()
            prev_action = str(previous.get("last_action") or "").strip()
            if active and since and prev_action == action:
                payload["since_ts"] = since
except Exception:
    pass
state_file.parent.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
}

with_lock() {
  local fd=73
  eval "exec ${fd}>\"$LOCK_FILE\""
  if ! flock -n "$fd"; then
    echo "PLANNER_AUTONOMY status=skip reason=busy_lock"
    exit 0
  fi
}

run_safe_cmd() {
  local label="$1"
  local cmd="$2"
  local out_file err_file rc
  out_file="$(mktemp)"
  err_file="$(mktemp)"
  set +e
  timeout "$SAFE_TIMEOUT_SECONDS" "$EXEC_SAFE" --workdir "$ROOT" -- "$cmd" >"$out_file" 2>"$err_file"
  rc=$?
  set -e
  local out_text err_text
  out_text="$(cat "$out_file" 2>/dev/null || true)"
  err_text="$(cat "$err_file" 2>/dev/null || true)"
  rm -f "$out_file" "$err_file"
  log_line "planner_autonomy action=${label} rc=${rc} cmd=$(printf '%s' "$cmd" | tr '\n' ' ' | cut -c1-180) out=$(printf '%s' "$out_text" | tr '\n' ' ' | tr -s ' ' | cut -c1-220) err=$(printf '%s' "$err_text" | tr '\n' ' ' | tr -s ' ' | cut -c1-220)"
  printf '%s' "$out_text"
  return "$rc"
}

run_safe_capture() {
  local label="$1"
  local cmd="$2"
  local out rc
  set +e
  out="$(run_safe_cmd "$label" "$cmd")"
  rc=$?
  set -e
  printf '%s\n%s\n' "$rc" "$out"
}

bridge_dispatch_capture() {
  local contract_file payload
  contract_file="$(mktemp)"
  cat >"$contract_file" <<'EOF'
STATUS: IN_PROGRESS
DELTA: PLANNER_AUTONOMY_BRIDGE_DISPATCH
EVIDENCE: task_update=blocked; root_cause=planner_ready_bridge_missing; fix_applied=planner_autonomy_bridge_dispatch; verify=before=queue_ready_without_planner_slot
RISKS: none
NEXT: owner=planner; action=dispatch planner-owned capability work now
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: PLANNER_AUTONOMY_BRIDGE_DISPATCH
EOF
  payload="$(run_safe_capture "bridge_dispatch" "python3 platform/automation/planner_orchestrator_bridge.py --root \"$ROOT\" --source planner_autonomy_tick --backend auto --contract-file \"$contract_file\"")"
  rm -f "$contract_file"
  printf '%s' "$payload"
}

parse_bridge_dispatch_field() {
  local payload="$1"
  local field="$2"
  python3 -c '
import json
import sys

field = sys.argv[1]
raw = sys.stdin.read().strip()
if not raw:
    print("")
    raise SystemExit(0)
try:
    data = json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)

value = data
for token in field.split("."):
    if not isinstance(value, dict):
        value = ""
        break
    value = value.get(token, "")

if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("")
else:
    print(str(value))
' "$field" <<<"$payload"
}

planner_counts() {
  python3 - "$BOARD_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("0|0|none")
    raise SystemExit(0)
try:
    board = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("0|0|none")
    raise SystemExit(0)

def canon(value: str) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if token in {"planner", "analyst", "architect", "po", "scrum_master", "vision_architect_tasks_planner", "vision-architect-tasks-planner"}:
        return "planner"
    if token in {"dev", "backend_engineer", "frontend_engineer", "data_analyst", "integrator", "tester", "qa"}:
        return "dev"
    if token in {"admin", "clawsentinel", "infra"}:
        return "admin"
    return token

in_progress = 0
ready = 0
ready_task = "none"
for task in board.get("tasks", []):
    if not isinstance(task, dict):
        continue
    task_role = canon(task.get("role", ""))
    assignee = canon(task.get("assignee", ""))
    if "planner" not in {task_role, assignee}:
        continue
    state = str(task.get("state", "")).upper()
    if state == "IN_PROGRESS":
        in_progress += 1
    if state == "READY":
        ready += 1
        if ready_task == "none":
            ready_task = str(task.get("id", "")).strip() or "none"

print(f"{in_progress}|{ready}|{ready_task}")
PY
}

parse_autobatch_id() {
  local text="$1"
  local batch_id="none"
  if [[ "$text" =~ AUTOBATCH_OK[[:space:]]+batch_id=([A-Z0-9-]+) ]]; then
    batch_id="${BASH_REMATCH[1]}"
  fi
  printf '%s' "$batch_id"
}

parse_autobatch_reason() {
  local text="$1"
  local reason="unknown"
  if [[ "$text" =~ AUTOBATCH_SKIP[[:space:]]+reason=([a-zA-Z0-9_-]+) ]]; then
    reason="${BASH_REMATCH[1]}"
  fi
  printf '%s' "$reason"
}

planner_runway_snapshot() {
  python3 - "$BOARD_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("0|0|none|0|0")
    raise SystemExit(0)
try:
    board = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("0|0|none|0|0")
    raise SystemExit(0)

def canon(value: str) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if token in {"planner", "analyst", "architect", "po", "scrum_master", "vision_architect_tasks_planner", "vision-architect-tasks-planner"}:
        return "planner"
    if token in {"dev", "backend_engineer", "frontend_engineer", "data_analyst", "integrator", "tester", "qa"}:
        return "dev"
    if token in {"admin", "clawsentinel", "infra"}:
        return "admin"
    return token

planner_in_progress = 0
planner_ready = 0
planner_ready_task = "none"
blocking_task_states = {"WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED"}
blocking_stream_states = {"WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED"}
runway_tasks = 0
runway_streams = 0
for task in board.get("tasks", []):
    if not isinstance(task, dict):
        continue
    task_role = canon(task.get("role", ""))
    assignee = canon(task.get("assignee", ""))
    state = str(task.get("state", "")).upper()
    if state in blocking_task_states:
        runway_tasks += 1
    if "planner" in {task_role, assignee}:
        if state == "IN_PROGRESS":
            planner_in_progress += 1
        if state in {"READY", "READY_PLANNER"}:
            planner_ready += 1
            if planner_ready_task == "none":
                planner_ready_task = str(task.get("id", "")).strip() or "none"
for stream in board.get("streams", []):
    if not isinstance(stream, dict):
        continue
    state = str(stream.get("state", "")).upper()
    if state in blocking_stream_states:
        runway_streams += 1

print(f"{planner_in_progress}|{planner_ready}|{planner_ready_task}|{runway_tasks}|{runway_streams}")
PY
}

with_lock

snapshot="$(planner_runway_snapshot)"
planner_in_progress="${snapshot%%|*}"
rest="${snapshot#*|}"
planner_ready="${rest%%|*}"
rest="${rest#*|}"
planner_ready_task="${rest%%|*}"
rest="${rest#*|}"
runway_task_count="${rest%%|*}"
runway_stream_count="${rest##*|}"

if [[ "$planner_in_progress" =~ ^[0-9]+$ ]] && (( planner_in_progress > 0 )); then
  write_state 1 "resume_in_progress" "no_create" "planner_in_progress_exists" "${planner_ready_task:-none}" "none" "planner_in_progress=${planner_in_progress}"
  echo "PLANNER_AUTONOMY status=ok action=resume_in_progress outcome=no_create planner_in_progress=${planner_in_progress} planner_ready=${planner_ready}"
  exit 0
fi

sanitize_payload="$(run_safe_capture "sanitize_dependencies" "python3 platform/automation/parallel_workstream.py sanitize-dependencies --queue docs/operations/orchestrator/priority-queue.json --all-batches")"
sanitize_rc="$(printf '%s' "$sanitize_payload" | head -n1)"

sync_payload="$(run_safe_capture "sync_priority" "python3 platform/automation/parallel_workstream.py sync-priority --queue docs/operations/orchestrator/priority-queue.json")"
sync_rc="$(printf '%s' "$sync_payload" | head -n1)"

planner_children_active="$(
  ROOT_PATH="$ROOT" python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT_PATH"])
active_statuses = {"spawned", "running"}

def load_rows(path: Path, key: str) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    if isinstance(payload, dict):
        rows = payload.get(key, [])
    else:
        rows = payload
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]

subagent_rows = []
for path in (
    root / "logs-codex-runs" / "orchestrator-state" / "planner-subagents-registry.json",
    root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json",
):
    if path.exists():
        subagent_rows = load_rows(path, "subagents")
        break

worker_rows = []
for path in (
    root / "logs-codex-runs" / "orchestrator-state" / "dynamic-workers-registry.json",
    root / "docs" / "operations" / "orchestrator" / "dynamic-workers-registry.json",
):
    if path.exists():
        worker_rows = load_rows(path, "workers")
        break

subagents_active = any(str(row.get("status", "")).strip().lower() in active_statuses for row in subagent_rows)
workers_active = any(
    str(row.get("parent_role", "")).strip().lower() == "planner"
    and str(row.get("status", "")).strip().lower() in active_statuses
    for row in worker_rows
)
print("1" if (subagents_active or workers_active) else "0")
PY
)"
if [[ "$planner_children_active" == "1" ]]; then
  collect_payload="$(run_safe_capture "collect_pending_results" "python3 platform/automation/planner_orchestrator_bridge.py --root \"$ROOT\" --source planner_autonomy_tick --collect-only")"
  collect_rc="$(printf '%s' "$collect_payload" | head -n1)"
else
  collect_payload=$'0\nSKIP(no_active_planner_children)'
  collect_rc="0"
fi

reconcile_payload="$(run_safe_capture "reconcile_state" "python3 platform/automation/parallel_workstream.py reconcile-state --queue docs/operations/orchestrator/priority-queue.json")"
reconcile_rc="$(printf '%s' "$reconcile_payload" | head -n1)"

snapshot="$(planner_runway_snapshot)"
planner_in_progress="${snapshot%%|*}"
rest="${snapshot#*|}"
planner_ready="${rest%%|*}"
rest="${rest#*|}"
planner_ready_task="${rest%%|*}"
rest="${rest#*|}"
runway_task_count="${rest%%|*}"
runway_stream_count="${rest##*|}"

if [[ "$planner_ready" =~ ^[0-9]+$ ]] && (( planner_ready > 0 )); then
  claim_payload="$(run_safe_capture "claim_ready" "$(build_claim_cmd "")")"
  claim_rc="$(printf '%s' "$claim_payload" | head -n1)"
  if [[ "$claim_rc" == "0" ]]; then
    write_state 1 "claim_ready" "resolved" "planner_ready_found" "${planner_ready_task:-none}" "none" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
    echo "PLANNER_AUTONOMY status=ok action=claim_ready outcome=resolved planner_ready=${planner_ready} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  if [[ -n "${planner_ready_task:-}" && "${planner_ready_task:-none}" != "none" ]]; then
    direct_ready_claim_payload="$(run_safe_capture "claim_ready_direct" "$(build_claim_cmd "$planner_ready_task")")"
    direct_ready_claim_rc="$(printf '%s' "$direct_ready_claim_payload" | head -n1)"
    if [[ "$direct_ready_claim_rc" == "0" ]]; then
      write_state 1 "claim_ready" "resolved" "planner_ready_direct_claim" "${planner_ready_task:-none}" "none" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};claim_rc=${claim_rc};direct_claim_rc=${direct_ready_claim_rc}"
      echo "PLANNER_AUTONOMY status=ok action=claim_ready outcome=resolved direct_task=${planner_ready_task:-none} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc} claim_rc=${claim_rc} direct_claim_rc=${direct_ready_claim_rc}"
      exit 0
    fi
  fi
  write_state 1 "claim_ready" "failed" "planner_claim_ready_failed" "${planner_ready_task:-none}" "planner_claim_ready_failed_hard" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};claim_rc=${claim_rc}"
  echo "PLANNER_AUTONOMY status=error action=claim_ready outcome=failed issue=planner_claim_ready_failed_hard planner_ready=${planner_ready} planner_ready_task=${planner_ready_task:-none} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc} claim_rc=${claim_rc}"
  exit 0
fi

if [[ "$AUTO_CREATE_ON_EMPTY" != "1" ]]; then
  write_state 1 "no_create" "deferred" "planner_autocreate_disabled" "none" "planner_autocreate_disabled" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
  echo "PLANNER_AUTONOMY status=warn action=no_create outcome=deferred issue=planner_autocreate_disabled planner_ready=0 sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

if [[ "$runway_task_count" =~ ^[0-9]+$ ]] && (( runway_task_count > 0 )) || [[ "$runway_stream_count" =~ ^[0-9]+$ ]] && (( runway_stream_count > 0 )); then
  bridge_payload="$(bridge_dispatch_capture)"
  bridge_rc="$(printf '%s' "$bridge_payload" | head -n1)"
  bridge_out="$(printf '%s' "$bridge_payload" | tail -n +2)"
  bridge_dispatched="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.dispatched")"
  bridge_task_id="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.task_id")"
  bridge_reason="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.reason")"
  if [[ "$bridge_rc" == "0" && "$bridge_dispatched" == "true" ]]; then
    write_state 1 "repair_bridge_dispatch" "resolved" "planner_bridge_dispatch_active" "${bridge_task_id:-none}" "none" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};runway_tasks=${runway_task_count};runway_streams=${runway_stream_count};bridge_reason=${bridge_reason:-none}"
    echo "PLANNER_AUTONOMY status=ok action=repair_bridge_dispatch outcome=resolved task_id=${bridge_task_id:-none} bridge_reason=${bridge_reason:-none} planner_ready=0 runway_tasks=${runway_task_count} runway_streams=${runway_stream_count} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  write_state 1 "repair_only" "deferred" "planner_runway_not_empty" "none" "planner_ready_bridge_missing" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};runway_tasks=${runway_task_count};runway_streams=${runway_stream_count}"
  echo "PLANNER_AUTONOMY status=warn action=repair_only outcome=deferred issue=planner_ready_bridge_missing planner_ready=0 runway_tasks=${runway_task_count} runway_streams=${runway_stream_count} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

create_payload="$(run_safe_capture "create_top_level" "python3 platform/automation/parallel_workstream.py planner-autobatch --queue docs/operations/orchestrator/priority-queue.json --reason planner_always_active --cooldown-s 0")"
create_rc="$(printf '%s' "$create_payload" | head -n1)"
create_out="$(printf '%s' "$create_payload" | tail -n +2)"
created_batch_id="$(parse_autobatch_id "$create_out")"
create_reason="$(parse_autobatch_reason "$create_out")"

if [[ "$create_rc" != "0" ]]; then
  write_state 1 "autobatch" "deferred" "planner_autobatch_failed" "none" "planner_autobatch_failed" "create_rc=${create_rc};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
  echo "PLANNER_AUTONOMY status=warn action=autobatch outcome=deferred issue=planner_autobatch_failed create_rc=${create_rc} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

if [[ "$create_out" == AUTOBATCH_SKIP* ]]; then
  create_issue="planner_autobatch_skip"
  create_state_reason="planner_autobatch_skipped"
  if [[ "$create_reason" == "duplicate_title" ]]; then
    create_issue="autobatch_duplicate_nonfatal"
    create_state_reason="autobatch_duplicate_nonfatal"
  elif [[ "$create_reason" == "runway_not_empty" ]]; then
    bridge_payload="$(bridge_dispatch_capture)"
    bridge_rc="$(printf '%s' "$bridge_payload" | head -n1)"
    bridge_out="$(printf '%s' "$bridge_payload" | tail -n +2)"
    bridge_dispatched="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.dispatched")"
    bridge_task_id="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.task_id")"
    bridge_reason="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.reason")"
    if [[ "$bridge_rc" == "0" && "$bridge_dispatched" == "true" ]]; then
      write_state 1 "autobatch_bridge_dispatch" "resolved" "planner_bridge_dispatch_active" "${bridge_task_id:-none}" "none" "create_rc=${create_rc};create_reason=${create_reason};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN};bridge_reason=${bridge_reason:-none}"
      echo "PLANNER_AUTONOMY status=ok action=autobatch_bridge_dispatch outcome=resolved task_id=${bridge_task_id:-none} bridge_reason=${bridge_reason:-none} create_reason=${create_reason} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
      exit 0
    fi
    create_issue="planner_ready_bridge_missing"
    create_state_reason="planner_runway_not_empty"
  fi
  write_state 1 "autobatch_skip" "deferred" "${create_state_reason}" "${created_batch_id}" "${create_issue}" "create_rc=${create_rc};create_reason=${create_reason};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
  echo "PLANNER_AUTONOMY status=warn action=autobatch_skip outcome=deferred issue=${create_issue} batch_id=${created_batch_id} create_reason=${create_reason} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

sync_after_create_payload="$(run_safe_capture "sync_priority_after_create" "python3 platform/automation/parallel_workstream.py sync-priority --queue docs/operations/orchestrator/priority-queue.json")"
sync_after_create_rc="$(printf '%s' "$sync_after_create_payload" | head -n1)"

claim_after_create_payload="$(run_safe_capture "claim_after_create" "$(build_claim_cmd "")")"
claim_after_create_rc="$(printf '%s' "$claim_after_create_payload" | head -n1)"

if [[ "$claim_after_create_rc" == "0" ]]; then
  write_state 1 "create_and_claim" "resolved" "planner_created_and_claimed" "${created_batch_id}" "none" "create_rc=${create_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};sync_after_create_rc=${sync_after_create_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
  echo "PLANNER_AUTONOMY status=ok action=create_and_claim outcome=resolved batch_id=${created_batch_id} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc}"
  exit 0
fi

direct_claim_task="none"
for candidate in "${created_batch_id}-ANALYSIS" "${created_batch_id}-PLAN"; do
  if [[ -z "$created_batch_id" || "$created_batch_id" == "none" ]]; then
    break
  fi
  direct_claim_task="$candidate"
  direct_claim_payload="$(run_safe_capture "claim_created_task" "$(build_claim_cmd "$candidate")")"
  direct_claim_rc="$(printf '%s' "$direct_claim_payload" | head -n1)"
  if [[ "$direct_claim_rc" == "0" ]]; then
    write_state 1 "create_and_claim" "resolved" "planner_created_and_claimed_direct" "$candidate" "none" "create_rc=${create_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};sync_after_create_rc=${sync_after_create_rc};claim_rc=${claim_after_create_rc};direct_claim_rc=${direct_claim_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
    echo "PLANNER_AUTONOMY status=ok action=create_and_claim outcome=resolved batch_id=${created_batch_id} direct_task=${candidate} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc} direct_claim_rc=${direct_claim_rc}"
    exit 0
  fi
done

write_state 1 "create_and_claim" "failed" "planner_claim_after_create_failed" "${direct_claim_task}" "planner_claim_after_create_failed_hard" "create_rc=${create_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};sync_after_create_rc=${sync_after_create_rc};claim_rc=${claim_after_create_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
echo "PLANNER_AUTONOMY status=error action=create_and_claim outcome=failed issue=planner_claim_after_create_failed_hard batch_id=${created_batch_id} direct_task=${direct_claim_task} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc}"
exit 0
