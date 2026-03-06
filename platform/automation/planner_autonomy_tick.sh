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

with_lock

counts="$(planner_counts)"
planner_in_progress="${counts%%|*}"
rest="${counts#*|}"
planner_ready="${rest%%|*}"
planner_ready_task="${rest##*|}"

if [[ "$planner_in_progress" =~ ^[0-9]+$ ]] && (( planner_in_progress > 0 )); then
  write_state 1 "resume_in_progress" "no_create" "planner_in_progress_exists" "${planner_ready_task:-none}" "none" "planner_in_progress=${planner_in_progress}"
  echo "PLANNER_AUTONOMY status=ok action=resume_in_progress outcome=no_create planner_in_progress=${planner_in_progress} planner_ready=${planner_ready}"
  exit 0
fi

sanitize_payload="$(run_safe_capture "sanitize_dependencies" "python3 platform/automation/parallel_workstream.py sanitize-dependencies --queue docs/operations/orchestrator/priority-queue.json --all-batches")"
sanitize_rc="$(printf '%s' "$sanitize_payload" | head -n1)"

sync_payload="$(run_safe_capture "sync_priority" "python3 platform/automation/parallel_workstream.py sync-priority --queue docs/operations/orchestrator/priority-queue.json")"
sync_rc="$(printf '%s' "$sync_payload" | head -n1)"

counts="$(planner_counts)"
planner_in_progress="${counts%%|*}"
rest="${counts#*|}"
planner_ready="${rest%%|*}"
planner_ready_task="${rest##*|}"

if [[ "$planner_ready" =~ ^[0-9]+$ ]] && (( planner_ready > 0 )); then
  claim_payload="$(run_safe_capture "claim_ready" "python3 platform/automation/parallel_workstream.py claim --role planner")"
  claim_rc="$(printf '%s' "$claim_payload" | head -n1)"
  if [[ "$claim_rc" == "0" ]]; then
    write_state 1 "claim_ready" "resolved" "planner_ready_found" "${planner_ready_task:-none}" "none" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc}"
    echo "PLANNER_AUTONOMY status=ok action=claim_ready outcome=resolved planner_ready=${planner_ready} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc}"
    exit 0
  fi
  write_state 1 "claim_ready" "deferred" "planner_claim_ready_failed" "${planner_ready_task:-none}" "planner_claim_ready_failed" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};claim_rc=${claim_rc}"
  echo "PLANNER_AUTONOMY status=warn action=claim_ready outcome=deferred issue=planner_claim_ready_failed planner_ready=${planner_ready} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} claim_rc=${claim_rc}"
  exit 0
fi

if [[ "$AUTO_CREATE_ON_EMPTY" != "1" ]]; then
  write_state 1 "no_create" "deferred" "planner_autocreate_disabled" "none" "planner_autocreate_disabled" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc}"
  echo "PLANNER_AUTONOMY status=warn action=no_create outcome=deferred issue=planner_autocreate_disabled planner_ready=0 sanitize_rc=${sanitize_rc} sync_rc=${sync_rc}"
  exit 0
fi

create_payload="$(run_safe_capture "create_top_level" "python3 platform/automation/parallel_workstream.py planner-autobatch --queue docs/operations/orchestrator/priority-queue.json --reason planner_always_active --cooldown-s 0")"
create_rc="$(printf '%s' "$create_payload" | head -n1)"
create_out="$(printf '%s' "$create_payload" | tail -n +2)"
created_batch_id="$(parse_autobatch_id "$create_out")"

sync_after_create_payload="$(run_safe_capture "sync_priority_after_create" "python3 platform/automation/parallel_workstream.py sync-priority --queue docs/operations/orchestrator/priority-queue.json")"
sync_after_create_rc="$(printf '%s' "$sync_after_create_payload" | head -n1)"

claim_after_create_payload="$(run_safe_capture "claim_after_create" "python3 platform/automation/parallel_workstream.py claim --role planner")"
claim_after_create_rc="$(printf '%s' "$claim_after_create_payload" | head -n1)"

if [[ "$claim_after_create_rc" == "0" ]]; then
  write_state 1 "create_and_claim" "resolved" "planner_created_and_claimed" "${created_batch_id}" "none" "create_rc=${create_rc};sync_rc=${sync_rc};sync_after_create_rc=${sync_after_create_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
  echo "PLANNER_AUTONOMY status=ok action=create_and_claim outcome=resolved batch_id=${created_batch_id} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc}"
  exit 0
fi

write_state 1 "create_and_claim" "deferred" "planner_claim_after_create_failed" "${created_batch_id}" "planner_claim_after_create_failed" "create_rc=${create_rc};sync_rc=${sync_rc};sync_after_create_rc=${sync_after_create_rc};claim_rc=${claim_after_create_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
echo "PLANNER_AUTONOMY status=warn action=create_and_claim outcome=deferred issue=planner_claim_after_create_failed batch_id=${created_batch_id} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc}"
exit 0
