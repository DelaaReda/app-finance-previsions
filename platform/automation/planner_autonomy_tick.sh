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
QUEUE_FILE="${FC_PLANNER_AUTONOMY_QUEUE_FILE:-${ROOT}/logs-codex-runs/orchestrator-state/priority-queue.json}"
BOARD_FILE="${FC_PLANNER_AUTONOMY_BOARD_FILE:-${ROOT}/logs-codex-runs/orchestrator-state/parallel-workstreams.json}"
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
  local cmd="python3 platform/automation/runtime/planner/planner_runtime_actions.py claim --board \"$BOARD_FILE\" --role planner"
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
  if ! command -v flock >/dev/null 2>&1; then
    local lock_dir="${LOCK_FILE}.d"
    if ! mkdir "$lock_dir" 2>/dev/null; then
      echo "PLANNER_AUTONOMY status=skip reason=busy_lock"
      exit 0
    fi
    trap 'rmdir "'"$lock_dir"'" 2>/dev/null || true' EXIT
    return 0
  fi
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
  if command -v timeout >/dev/null 2>&1; then
    timeout "$SAFE_TIMEOUT_SECONDS" "$EXEC_SAFE" --workdir "$ROOT" -- "$cmd" >"$out_file" 2>"$err_file"
    rc=$?
  else
    "$EXEC_SAFE" --workdir "$ROOT" -- "$cmd" >"$out_file" 2>"$err_file"
    rc=$?
  fi
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

capture_rc() {
  local payload="$1"
  printf '%s' "${payload%%$'\n'*}"
}

capture_body() {
  local payload="$1"
  if [[ "$payload" == *$'\n'* ]]; then
    printf '%s' "${payload#*$'\n'}"
  fi
}

runtime_dispatch_capture() {
  local contract_file payload
  contract_file="$(mktemp)"
  cat >"$contract_file" <<'EOF'
STATUS: IN_PROGRESS
DELTA: PLANNER_AUTONOMY_RUNTIME_DISPATCH
EVIDENCE: task_update=blocked; root_cause=planner_ready_runtime_dispatch_missing; fix_applied=planner_autonomy_runtime_dispatch; verify=before=queue_ready_without_planner_slot
RISKS: none
NEXT: owner=planner; action=dispatch planner-owned capability work now
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: PLANNER_AUTONOMY_RUNTIME_DISPATCH
EOF
  payload="$(run_safe_capture "runtime_dispatch" "python3 platform/automation/runtime/planner/planner_runtime_actions.py --root \"$ROOT\" --source planner_autonomy_tick --backend auto --contract-file \"$contract_file\"")"
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

novelty_guard_snapshot() {
  ROOT_PATH="$ROOT" AUTOMATION_DIR="$SCRIPT_DIR" python3 - <<'PY'
import importlib.util
import os
import sys
from pathlib import Path

root = Path(os.environ["ROOT_PATH"])
automation_dir = Path(os.environ["AUTOMATION_DIR"]).resolve()
guard_path = root / "platform" / "automation" / "product_priority_guard.py"
if not guard_path.exists():
    guard_path = automation_dir / "product_priority_guard.py"
spec = importlib.util.spec_from_file_location("fc_product_priority_guard", guard_path)
if spec is None or spec.loader is None:
    print("1|guard_missing|none|none")
    raise SystemExit(0)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = module.build_autobatch_novelty_gate(root)
allow = "1" if bool(payload.get("allow_autobatch", True)) else "0"
reason = str(payload.get("reason") or "none").strip() or "none"
scope = str(payload.get("repeated_scope") or "none").strip() or "none"
recent = ",".join(
    str(item.get("classification") or "unknown")
    for item in payload.get("recent_batches", [])
    if isinstance(item, dict)
) or "none"
print(f"{allow}|{reason}|{scope}|{recent}")
PY
}

active_capability_dispatch_snapshot() {
  python3 - "$BOARD_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("none|none|none|0|none|none")
    raise SystemExit(0)
try:
    board = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("none|none|none|0|none|none")
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

def task_batch_id(task: dict) -> str:
    stream_id = str(task.get("stream_id") or task.get("batch_id") or "").strip().upper()
    if stream_id:
        return stream_id
    task_id = str(task.get("id") or task.get("task_id") or "").strip().upper()
    if task_id.startswith("BATCH-"):
        parts = task_id.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:2])
    return ""

def priority_rank(token: str) -> int:
    raw = str(token or "").strip().upper()
    if raw.startswith("P") and raw[1:].isdigit():
        return int(raw[1:])
    return 9

def op_state(task: dict | None) -> str:
    if not isinstance(task, dict):
        return ""
    status = str(task.get("status") or "").strip().upper()
    state = str(task.get("state") or "").strip().upper()
    if status in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED", "WAITING_DEP", "DONE", "CLOSED"}:
        return status
    return state or status

active_cycle = board.get("active_cycle")
if not isinstance(active_cycle, dict):
    active_cycle = {}
active_ids = {
    str(item).strip().upper()
    for item in active_cycle.get("active_batch_ids", [])
    if str(item).strip()
}
if not active_ids:
    print("none|none|none|0|none|none")
    raise SystemExit(0)

tasks = board.get("tasks", [])
index = {}
if isinstance(tasks, list):
    for task in tasks:
        if isinstance(task, dict):
            task_id = str(task.get("id") or task.get("task_id") or "").strip()
            if task_id:
                index[task_id] = task

candidates = []
role_order = {"admin": 0, "dev": 1}
for idx, task in enumerate(tasks if isinstance(tasks, list) else []):
    if not isinstance(task, dict):
        continue
    role = canon(task.get("role", ""))
    if role not in {"admin", "dev"}:
        continue
    state = op_state(task)
    if state not in {"READY", "READY_PLANNER"}:
        continue
    batch_id = task_batch_id(task)
    if batch_id not in active_ids:
        continue
    deps = [str(dep).strip() for dep in task.get("depends_on", []) if str(dep).strip()]
    if any(op_state(index.get(dep, {})) not in {"DONE", "CLOSED"} for dep in deps):
        continue
    next_action = str(task.get("next_action") or "").strip()
    planner_takeover = bool(task.get("planner_takeover_required"))
    if not (planner_takeover or "retry_capability" in next_action.lower() or state == "READY_PLANNER"):
        continue
    candidates.append(
        (
            role_order.get(role, 9),
            priority_rank(task.get("priority", "P9")),
            idx,
            str(task.get("id") or task.get("task_id") or "none").strip() or "none",
            role,
            state,
            "1" if planner_takeover else "0",
            next_action or "none",
            str(task.get("blocked_reason") or "none").strip() or "none",
        )
    )

if not candidates:
    print("none|none|none|0|none|none")
    raise SystemExit(0)

candidates.sort()
_, _, _, task_id, role, state, planner_takeover, next_action, blocked_reason = candidates[0]
print(f"{role}|{task_id}|{state}|{planner_takeover}|{next_action}|{blocked_reason}")
PY
}

delivery_state_snapshot() {
  ROOT_PATH="$ROOT" AUTOMATION_DIR="$SCRIPT_DIR" DELIVERY_EC2_REACHABLE="${FC_PLANNER_AUTONOMY_EC2_REACHABLE:-}" python3 - <<'PY'
import os
from pathlib import Path
import sys

root = Path(os.environ["ROOT_PATH"])
automation_dir = Path(os.environ["AUTOMATION_DIR"]).resolve()
if str(automation_dir) not in sys.path:
    sys.path.insert(0, str(automation_dir))

from runtime.truth.public_runtime_probe import probe_public_surface
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot

raw_reachable = str(os.environ.get("DELIVERY_EC2_REACHABLE", "") or "").strip().lower()
maintenance_active = False
maintenance_details = {}
public_probe_status = "unknown"
if raw_reachable in {"1", "true", "yes", "ok"}:
    ec2_reachable = True
    public_probe_status = "ok"
elif raw_reachable in {"0", "false", "no", "error"}:
    ec2_reachable = False
    public_probe_status = "error"
else:
    base_url = str(os.environ.get("FC_PUBLIC_APP_BASE_URL") or os.environ.get("FC_API_BASE_URL") or "http://3.98.20.77").strip() or "http://3.98.20.77"
    url = f"{base_url.rstrip('/')}/api/health"
    probe = probe_public_surface(url, timeout_s=1.5)
    maintenance_active = bool(probe.get("maintenance_active"))
    maintenance_details = probe
    if probe.get("http_ok"):
        ec2_reachable = True
        public_probe_status = "ok"
    elif maintenance_active:
        ec2_reachable = True
        public_probe_status = "degraded"
    else:
        ec2_reachable = False
        public_probe_status = "error"

snapshot = build_runtime_truth_snapshot(
    root,
    state_limit=24,
    event_limit=24,
    ec2_reachable=ec2_reachable,
    public_probe_status=public_probe_status,
    maintenance_active=maintenance_active,
    maintenance_details=maintenance_details,
    persist_delivery_state=True,
)
state = snapshot.get("product_delivery_state", {}) if isinstance(snapshot, dict) else {}
phase = str(state.get("phase") or "idle_ready_for_next_batch").strip() or "idle_ready_for_next_batch"
active_batch = str(state.get("active_batch_id") or "none").strip() or "none"
next_batch_eligible = "1" if bool(state.get("next_batch_eligible")) else "0"
freeze_reason = str(state.get("freeze_reason") or "none").strip() or "none"
product_done = "1" if bool(state.get("product_done")) else "0"
ops_clean = "1" if bool(state.get("ops_clean")) else "0"
ec2_reachable = "1" if bool(state.get("ec2_reachable")) else "0"
print(f"{phase}|{active_batch}|{next_batch_eligible}|{freeze_reason}|{product_done}|{ops_clean}|{ec2_reachable}")
PY
}

parse_kv_field() {
  local payload="$1"
  local field="$2"
  python3 - "$field" <<'PY' <<<"$payload"
import sys

field = sys.argv[1]
raw = sys.stdin.read().strip()
if not raw:
    print("")
    raise SystemExit(0)
tokens = raw.split()
values = {}
for token in tokens[1:]:
    if "=" not in token:
        continue
    key, value = token.split("=", 1)
    values[key] = value
print(values.get(field, ""))
PY
}

dispatch_capability_capture() {
  local role="$1"
  local payload
  payload="$(run_safe_capture "dispatch_${role}_capability" "python3 platform/automation/runtime/planner/planner_runtime_actions.py dispatch-capability --root \"$ROOT\" --source planner_autonomy_tick --backend auto --target-role \"$role\"")"
  printf '%s' "$payload"
}

public_proof_capture() {
  local batch_id="$1"
  local payload
  payload="$(run_safe_capture "public_proof" "python3 platform/automation/runtime/planner/planner_runtime_actions.py public-proof --root \"$ROOT\" --batch-id \"$batch_id\"")"
  printf '%s' "$payload"
}

with_lock

delivery_snapshot="$(delivery_state_snapshot)"
delivery_phase="${delivery_snapshot%%|*}"
delivery_rest="${delivery_snapshot#*|}"
delivery_active_batch="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_next_batch_eligible="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_freeze_reason="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_product_done="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_ops_clean="${delivery_rest%%|*}"
delivery_ec2_reachable="${delivery_rest##*|}"

if [[ "$delivery_phase" == "external_outage" ]]; then
  write_state 0 "delivery_governor" "deferred" "external_outage" "${delivery_active_batch:-none}" "external_outage" "phase=${delivery_phase};freeze_reason=${delivery_freeze_reason};ec2_reachable=${delivery_ec2_reachable}"
  echo "PLANNER_AUTONOMY status=warn action=delivery_governor outcome=deferred issue=external_outage phase=${delivery_phase} freeze_reason=${delivery_freeze_reason} ec2_reachable=${delivery_ec2_reachable}"
  exit 0
fi

if [[ "$delivery_phase" == "verifying_public_proof" && -n "$delivery_active_batch" && "$delivery_active_batch" != "none" ]]; then
  public_proof_payload="$(public_proof_capture "$delivery_active_batch")"
  public_proof_rc="$(capture_rc "$public_proof_payload")"
  public_proof_out="$(capture_body "$public_proof_payload")"
  public_proof_status="$(parse_kv_field "$public_proof_out" "status")"
  public_proof_batch_id="$(parse_kv_field "$public_proof_out" "batch_id")"
  public_proof_api_status="$(parse_kv_field "$public_proof_out" "api_smoke_status")"
  public_proof_ui_status="$(parse_kv_field "$public_proof_out" "ui_smoke_status")"
  public_proof_ref="$(parse_kv_field "$public_proof_out" "proof_ref")"

  if [[ "$public_proof_rc" != "0" ]]; then
    write_state 1 "public_proof" "failed" "public_proof_runner_failed" "${delivery_active_batch}" "public_proof_runner_failed" "batch_id=${delivery_active_batch};proof_rc=${public_proof_rc}"
    echo "PLANNER_AUTONOMY status=error action=public_proof outcome=failed issue=public_proof_runner_failed batch_id=${delivery_active_batch} proof_rc=${public_proof_rc}"
    exit 0
  fi

  delivery_snapshot="$(delivery_state_snapshot)"
  delivery_phase="${delivery_snapshot%%|*}"
  delivery_rest="${delivery_snapshot#*|}"
  delivery_active_batch="${delivery_rest%%|*}"
  delivery_rest="${delivery_rest#*|}"
  delivery_next_batch_eligible="${delivery_rest%%|*}"
  delivery_rest="${delivery_rest#*|}"
  delivery_freeze_reason="${delivery_rest%%|*}"
  delivery_rest="${delivery_rest#*|}"
  delivery_product_done="${delivery_rest%%|*}"
  delivery_rest="${delivery_rest#*|}"
  delivery_ops_clean="${delivery_rest%%|*}"
  delivery_ec2_reachable="${delivery_rest##*|}"

  if [[ "$delivery_phase" == "external_outage" ]]; then
    write_state 0 "public_proof" "deferred" "external_outage" "${public_proof_batch_id:-none}" "external_outage" "status=${public_proof_status:-unknown};proof_ref=${public_proof_ref:-none};ec2_reachable=${delivery_ec2_reachable}"
    echo "PLANNER_AUTONOMY status=warn action=public_proof outcome=deferred issue=external_outage batch_id=${public_proof_batch_id:-none} proof_status=${public_proof_status:-unknown} ec2_reachable=${delivery_ec2_reachable}"
    exit 0
  fi

  if [[ "$public_proof_status" == "maintenance" ]]; then
    write_state 1 "public_proof" "deferred" "runtime_restart_in_progress" "${public_proof_batch_id:-none}" "runtime_restart_in_progress" "status=${public_proof_status};proof_ref=${public_proof_ref:-none}"
    echo "PLANNER_AUTONOMY status=warn action=public_proof outcome=deferred issue=runtime_restart_in_progress batch_id=${public_proof_batch_id:-none} proof_status=${public_proof_status} proof_ref=${public_proof_ref:-none}"
    exit 0
  fi

  if [[ "$delivery_phase" == "verifying_public_proof" && -n "$delivery_active_batch" && "$delivery_active_batch" != "none" ]]; then
    write_state 1 "public_proof" "deferred" "waiting_public_proof" "${delivery_active_batch}" "waiting_public_proof" "status=${public_proof_status:-unknown};api=${public_proof_api_status:-unknown};ui=${public_proof_ui_status:-unknown};proof_ref=${public_proof_ref:-none}"
    echo "PLANNER_AUTONOMY status=warn action=public_proof outcome=deferred issue=waiting_public_proof batch_id=${delivery_active_batch} proof_status=${public_proof_status:-unknown} api_status=${public_proof_api_status:-unknown} ui_status=${public_proof_ui_status:-unknown}"
    exit 0
  fi
fi

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

sanitize_payload="$(run_safe_capture "sanitize_dependencies" "python3 platform/automation/runtime/planner/planner_runtime_actions.py sanitize-dependencies --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\" --all-batches")"
sanitize_rc="$(capture_rc "$sanitize_payload")"

sync_payload="$(run_safe_capture "sync_priority" "python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\"")"
sync_rc="$(capture_rc "$sync_payload")"

planner_children_active="$(
  ROOT_PATH="$ROOT" AUTOMATION_DIR="$SCRIPT_DIR" python3 - <<'PY'
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["ROOT_PATH"])
automation_dir = Path(os.environ["AUTOMATION_DIR"]).resolve()
active_statuses = {"spawned", "running"}

if str(automation_dir) not in sys.path:
    sys.path.insert(0, str(automation_dir))

from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot
from orchestrator_paths import resolve_orchestrator_read_path

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

runtime_truth = build_runtime_truth_snapshot(root, state_limit=64, event_limit=64)
if bool(runtime_truth.get("event_store_primary", False)):
    graph_active_statuses = {"running", "pending", "review", "in_progress", "blocked", "ready_to_merge", "retryable"}
    subagents_active = any(
        isinstance(row, dict)
        and str(row.get("owner_role", "")).strip().lower() == "planner"
        and str(row.get("target_role", "")).strip().lower() in {"dev", "admin", "scrum_master"}
        and str(row.get("status", "")).strip().lower() in graph_active_statuses
        for row in (runtime_truth.get("latest_states") if isinstance(runtime_truth.get("latest_states"), list) else [])
    )
    workers_active = False
else:
    subagents_active = False
    workers_active = False
print("1" if (subagents_active or workers_active) else "0")
PY
)"
if [[ "$planner_children_active" == "1" ]]; then
  collect_payload="$(run_safe_capture "collect_pending_results" "python3 platform/automation/runtime/planner/planner_runtime_actions.py --root \"$ROOT\" --source planner_autonomy_tick --collect-only")"
  collect_rc="$(capture_rc "$collect_payload")"
else
  collect_payload=$'0\nSKIP(no_active_planner_children)'
  collect_rc="0"
fi

reconcile_payload="$(run_safe_capture "reconcile_state" "python3 platform/automation/runtime/planner/planner_runtime_actions.py reconcile-state --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\"")"
reconcile_rc="$(capture_rc "$reconcile_payload")"

novelty_snapshot="$(novelty_guard_snapshot)"
novelty_allow="${novelty_snapshot%%|*}"
novelty_rest="${novelty_snapshot#*|}"
novelty_reason="${novelty_rest%%|*}"
novelty_rest="${novelty_rest#*|}"
novelty_scope="${novelty_rest%%|*}"
novelty_recent_classes="${novelty_rest#*|}"

delivery_snapshot="$(delivery_state_snapshot)"
delivery_phase="${delivery_snapshot%%|*}"
delivery_rest="${delivery_snapshot#*|}"
delivery_active_batch="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_next_batch_eligible="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_freeze_reason="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_product_done="${delivery_rest%%|*}"
delivery_rest="${delivery_rest#*|}"
delivery_ops_clean="${delivery_rest%%|*}"
delivery_ec2_reachable="${delivery_rest##*|}"

if [[ "$novelty_allow" != "1" ]]; then
  write_state 1 "novelty_guard" "deferred" "planner_stagnation_requires_novelty_target" "none" "planner_stagnation_requires_novelty_target" "reason=${novelty_reason};scope=${novelty_scope};recent_classes=${novelty_recent_classes};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
  echo "PLANNER_AUTONOMY status=warn action=novelty_guard outcome=deferred issue=planner_stagnation_requires_novelty_target reason=${novelty_reason} scope=${novelty_scope} recent_classes=${novelty_recent_classes} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

snapshot="$(planner_runway_snapshot)"
planner_in_progress="${snapshot%%|*}"
rest="${snapshot#*|}"
planner_ready="${rest%%|*}"
rest="${rest#*|}"
planner_ready_task="${rest%%|*}"
rest="${rest#*|}"
runway_task_count="${rest%%|*}"
runway_stream_count="${rest##*|}"

capability_dispatch_snapshot="$(active_capability_dispatch_snapshot)"
capability_ready_role="${capability_dispatch_snapshot%%|*}"
capability_dispatch_rest="${capability_dispatch_snapshot#*|}"
capability_ready_task="${capability_dispatch_rest%%|*}"
capability_dispatch_rest="${capability_dispatch_rest#*|}"
capability_ready_state="${capability_dispatch_rest%%|*}"
capability_dispatch_rest="${capability_dispatch_rest#*|}"
capability_takeover_required="${capability_dispatch_rest%%|*}"
capability_dispatch_rest="${capability_dispatch_rest#*|}"
capability_next_action="${capability_dispatch_rest%%|*}"
capability_blocked_reason="${capability_dispatch_rest#*|}"

if [[ "$planner_in_progress" == "0" && "$planner_ready" == "0" && -n "$capability_ready_role" && "$capability_ready_role" != "none" && -n "$capability_ready_task" && "$capability_ready_task" != "none" ]]; then
  targeted_dispatch_payload="$(dispatch_capability_capture "$capability_ready_role")"
  targeted_dispatch_rc="$(capture_rc "$targeted_dispatch_payload")"
  targeted_dispatch_out="$(capture_body "$targeted_dispatch_payload")"
  targeted_dispatch_reason="$(parse_kv_field "$targeted_dispatch_out" "reason")"
  targeted_dispatch_task="$(parse_kv_field "$targeted_dispatch_out" "task_id")"
  targeted_dispatch_backend="$(parse_kv_field "$targeted_dispatch_out" "backend")"
  if [[ "$targeted_dispatch_rc" == "0" && "$targeted_dispatch_out" == DISPATCH_OK* ]]; then
    write_state 1 "dispatch_ready_capability" "resolved" "planner_${capability_ready_role}_dispatch_active" "${targeted_dispatch_task:-$capability_ready_task}" "none" "role=${capability_ready_role};candidate_task=${capability_ready_task};candidate_state=${capability_ready_state};planner_takeover_required=${capability_takeover_required};next_action=${capability_next_action};blocked_reason=${capability_blocked_reason};backend=${targeted_dispatch_backend:-none};dispatch_reason=${targeted_dispatch_reason:-none};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
    echo "PLANNER_AUTONOMY status=ok action=dispatch_ready_capability outcome=resolved role=${capability_ready_role} task_id=${targeted_dispatch_task:-$capability_ready_task} backend=${targeted_dispatch_backend:-none} dispatch_reason=${targeted_dispatch_reason:-none} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  write_state 1 "dispatch_ready_capability" "deferred" "planner_${capability_ready_role}_dispatch_not_materialized" "${capability_ready_task}" "planner_${capability_ready_role}_dispatch_not_materialized" "role=${capability_ready_role};candidate_state=${capability_ready_state};planner_takeover_required=${capability_takeover_required};next_action=${capability_next_action};blocked_reason=${capability_blocked_reason};dispatch_reason=${targeted_dispatch_reason:-none};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
  echo "PLANNER_AUTONOMY status=warn action=dispatch_ready_capability outcome=deferred issue=planner_${capability_ready_role}_dispatch_not_materialized role=${capability_ready_role} task_id=${capability_ready_task} candidate_state=${capability_ready_state} planner_takeover_required=${capability_takeover_required} dispatch_reason=${targeted_dispatch_reason:-none} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

if [[ "$planner_ready" =~ ^[0-9]+$ ]] && (( planner_ready > 0 )); then
  claim_payload="$(run_safe_capture "claim_ready" "$(build_claim_cmd "")")"
  claim_rc="$(capture_rc "$claim_payload")"
  if [[ "$claim_rc" == "0" ]]; then
    write_state 1 "claim_ready" "resolved" "planner_ready_found" "${planner_ready_task:-none}" "none" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
    echo "PLANNER_AUTONOMY status=ok action=claim_ready outcome=resolved planner_ready=${planner_ready} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  if [[ -n "${planner_ready_task:-}" && "${planner_ready_task:-none}" != "none" ]]; then
    direct_ready_claim_payload="$(run_safe_capture "claim_ready_direct" "$(build_claim_cmd "$planner_ready_task")")"
    direct_ready_claim_rc="$(capture_rc "$direct_ready_claim_payload")"
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

if [[ "$delivery_phase" != "product_done_ops_dirty" && "$delivery_phase" != "idle_ready_for_next_batch" ]] && { [[ "$runway_task_count" =~ ^[0-9]+$ ]] && (( runway_task_count > 0 )) || [[ "$runway_stream_count" =~ ^[0-9]+$ ]] && (( runway_stream_count > 0 )); }; then
  bridge_payload="$(runtime_dispatch_capture)"
  bridge_rc="$(capture_rc "$bridge_payload")"
  bridge_out="$(capture_body "$bridge_payload")"
  bridge_dispatched="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.dispatched")"
  bridge_task_id="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.task_id")"
  bridge_reason="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.reason")"
  if [[ "$bridge_rc" == "0" && "$bridge_dispatched" == "true" ]]; then
    write_state 1 "repair_runtime_dispatch" "resolved" "planner_runtime_dispatch_active" "${bridge_task_id:-none}" "none" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};runway_tasks=${runway_task_count};runway_streams=${runway_stream_count};bridge_reason=${bridge_reason:-none}"
    echo "PLANNER_AUTONOMY status=ok action=repair_runtime_dispatch outcome=resolved task_id=${bridge_task_id:-none} bridge_reason=${bridge_reason:-none} planner_ready=0 runway_tasks=${runway_task_count} runway_streams=${runway_stream_count} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  write_state 1 "repair_only" "deferred" "planner_runway_not_empty" "none" "planner_ready_runtime_dispatch_missing" "sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};runway_tasks=${runway_task_count};runway_streams=${runway_stream_count}"
  echo "PLANNER_AUTONOMY status=warn action=repair_only outcome=deferred issue=planner_ready_runtime_dispatch_missing planner_ready=0 runway_tasks=${runway_task_count} runway_streams=${runway_stream_count} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

active_batch_ids="$delivery_active_batch"
active_cycle_id="canonical_delivery_state"

if [[ -n "$active_batch_ids" && "$active_batch_ids" != "none" ]]; then
  handoff_stale_seconds="${FC_CANONICAL_HANDOFF_STALE_SECONDS:-1800}"
  stale_handoff_snapshot="$(
    ACTIVE_BATCH_IDS="$active_batch_ids" BOARD_PATH="$BOARD_FILE" HANDOFF_STALE_SECONDS="$handoff_stale_seconds" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def parse_dt(raw: object) -> datetime | None:
    token = str(raw or "").strip()
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def task_batch_id(task: dict) -> str:
    stream_id = str(task.get("stream_id") or task.get("batch_id") or "").strip().upper()
    if stream_id:
        return stream_id
    task_id = str(task.get("id") or task.get("task_id") or "").strip().upper()
    if task_id.startswith("BATCH-"):
        parts = task_id.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:2])
    return ""


active_ids = {token.strip().upper() for token in str(os.environ.get("ACTIVE_BATCH_IDS", "")).split(",") if token.strip()}
board_path = Path(os.environ["BOARD_PATH"])
threshold = max(300, int(os.environ.get("HANDOFF_STALE_SECONDS", "1800")))
try:
    board = json.loads(board_path.read_text(encoding="utf-8", errors="ignore"))
except Exception:
    print("none|none|0|none")
    raise SystemExit(0)

tasks = board.get("tasks", [])
if not isinstance(tasks, list):
    print("none|none|0|none")
    raise SystemExit(0)

now = datetime.now(timezone.utc)
stale_candidates: list[tuple[int, str, str, str]] = []
for task in tasks:
    if not isinstance(task, dict):
        continue
    batch_id = task_batch_id(task)
    if batch_id not in active_ids:
        continue
    role = str(task.get("role") or "").strip().lower()
    state = str(task.get("state") or "").strip().upper()
    if role not in {"admin", "dev"} or state != "IN_PROGRESS":
        continue
    if any(str(task.get(field) or "").strip() for field in ("artifact", "runtime_artifact", "verify", "summary", "last_meaningful_progress_at")):
        continue
    baseline = parse_dt(task.get("started_at")) or parse_dt(task.get("updated_at")) or parse_dt(task.get("last_progress_at"))
    if baseline is None:
        continue
    age_s = max(0, int((now - baseline).total_seconds()))
    if age_s >= threshold:
        task_id = str(task.get("id") or task.get("task_id") or "none").strip() or "none"
        stale_candidates.append((age_s, task_id, role, batch_id))

if not stale_candidates:
    print("none|none|0|none")
    raise SystemExit(0)

stale_candidates.sort(reverse=True)
age_s, task_id, role, batch_id = stale_candidates[0]
print(f"{task_id}|{role}|{age_s}|{batch_id}")
PY
  )"
  stale_handoff_task="${stale_handoff_snapshot%%|*}"
  stale_handoff_role="$(printf '%s' "$stale_handoff_snapshot" | cut -d'|' -f2)"
  stale_handoff_age_s="$(printf '%s' "$stale_handoff_snapshot" | cut -d'|' -f3)"
  stale_handoff_batch="$(printf '%s' "$stale_handoff_snapshot" | cut -d'|' -f4)"
  if [[ -n "$stale_handoff_task" && "$stale_handoff_task" != "none" ]]; then
    write_state 1 "active_cycle_guard" "deferred" "planner_blocked_canonical_handoff" "$stale_handoff_task" "canonical_handoff_stale" "active_cycle=${active_batch_ids};cycle_id=${active_cycle_id};stale_task=${stale_handoff_task};stale_role=${stale_handoff_role};stale_batch=${stale_handoff_batch};stale_age_s=${stale_handoff_age_s};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc}"
    echo "PLANNER_AUTONOMY status=warn action=active_cycle_guard outcome=deferred issue=canonical_handoff_stale active_cycle=${active_batch_ids} cycle_id=${active_cycle_id} task_id=${stale_handoff_task} role=${stale_handoff_role} age_s=${stale_handoff_age_s} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  create_payload="$(run_safe_capture "create_top_level_queued" "python3 platform/automation/runtime/planner/planner_runtime_actions.py planner-autobatch --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\" --reason planner_active_cycle_queue_next --cooldown-s 0 --allow-active-queued")"
  create_rc="$(capture_rc "$create_payload")"
  create_out="$(capture_body "$create_payload")"
  created_batch_id="$(parse_autobatch_id "$create_out")"
  create_reason="$(parse_autobatch_reason "$create_out")"
  if [[ "$create_rc" == "0" && "$create_out" == AUTOBATCH_OK* ]]; then
    sync_after_create_payload="$(run_safe_capture "sync_priority_after_queued_create" "python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\"")"
    sync_after_create_rc="$(capture_rc "$sync_after_create_payload")"
    write_state 0 "autobatch_queue_next" "resolved" "planner_active_cycle_queue_next" "${created_batch_id}" "none" "active_cycle=${active_batch_ids};cycle_id=${active_cycle_id};created_batch=${created_batch_id};create_reason=${create_reason:-created};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};post_sync_rc=${sync_after_create_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
    echo "PLANNER_AUTONOMY status=ok action=autobatch_queue_next outcome=resolved active_cycle=${active_batch_ids} cycle_id=${active_cycle_id} batch_id=${created_batch_id} create_reason=${create_reason:-created} post_sync_rc=${sync_after_create_rc} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
    exit 0
  fi
  write_state 1 "autobatch_guard" "deferred" "planner_active_cycle_pinned" "${active_batch_ids}" "planner_active_cycle_pinned" "active_cycle=${active_batch_ids};cycle_id=${active_cycle_id};create_rc=${create_rc};create_reason=${create_reason:-none};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
  echo "PLANNER_AUTONOMY status=warn action=autobatch_guard outcome=deferred issue=planner_active_cycle_pinned active_cycle=${active_batch_ids} cycle_id=${active_cycle_id} create_rc=${create_rc} create_reason=${create_reason:-none} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

create_payload="$(run_safe_capture "create_top_level" "python3 platform/automation/runtime/planner/planner_runtime_actions.py planner-autobatch --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\" --reason planner_always_active --cooldown-s 0")"
create_rc="$(capture_rc "$create_payload")"
create_out="$(capture_body "$create_payload")"
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
  elif [[ "$create_reason" == "stagnation_requires_novelty_target" || "$create_reason" == "stagnation_alert" ]]; then
    create_issue="planner_stagnation_requires_novelty_target"
    create_state_reason="planner_stagnation_requires_novelty_target"
  elif [[ "$create_reason" == "runway_not_empty" ]]; then
    bridge_payload="$(runtime_dispatch_capture)"
    bridge_rc="$(capture_rc "$bridge_payload")"
    bridge_out="$(capture_body "$bridge_payload")"
    bridge_dispatched="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.dispatched")"
    bridge_task_id="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.task_id")"
    bridge_reason="$(parse_bridge_dispatch_field "$bridge_out" "dispatch.reason")"
    if [[ "$bridge_rc" == "0" && "$bridge_dispatched" == "true" ]]; then
      write_state 1 "autobatch_runtime_dispatch" "resolved" "planner_runtime_dispatch_active" "${bridge_task_id:-none}" "none" "create_rc=${create_rc};create_reason=${create_reason};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN};bridge_reason=${bridge_reason:-none}"
      echo "PLANNER_AUTONOMY status=ok action=autobatch_runtime_dispatch outcome=resolved task_id=${bridge_task_id:-none} bridge_reason=${bridge_reason:-none} create_reason=${create_reason} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
      exit 0
    fi
    create_issue="planner_ready_runtime_dispatch_missing"
    create_state_reason="planner_runway_not_empty"
  fi
  write_state 1 "autobatch_skip" "deferred" "${create_state_reason}" "${created_batch_id}" "${create_issue}" "create_rc=${create_rc};create_reason=${create_reason};sanitize_rc=${sanitize_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
  echo "PLANNER_AUTONOMY status=warn action=autobatch_skip outcome=deferred issue=${create_issue} batch_id=${created_batch_id} create_reason=${create_reason} sanitize_rc=${sanitize_rc} sync_rc=${sync_rc} collect_rc=${collect_rc} reconcile_rc=${reconcile_rc}"
  exit 0
fi

sync_after_create_payload="$(run_safe_capture "sync_priority_after_create" "python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board \"$BOARD_FILE\" --queue \"$QUEUE_FILE\"")"
sync_after_create_rc="$(capture_rc "$sync_after_create_payload")"

claim_after_create_payload="$(run_safe_capture "claim_after_create" "$(build_claim_cmd "")")"
claim_after_create_rc="$(capture_rc "$claim_after_create_payload")"

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
  direct_claim_rc="$(capture_rc "$direct_claim_payload")"
  if [[ "$direct_claim_rc" == "0" ]]; then
    write_state 1 "create_and_claim" "resolved" "planner_created_and_claimed_direct" "$candidate" "none" "create_rc=${create_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};sync_after_create_rc=${sync_after_create_rc};claim_rc=${claim_after_create_rc};direct_claim_rc=${direct_claim_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
    echo "PLANNER_AUTONOMY status=ok action=create_and_claim outcome=resolved batch_id=${created_batch_id} direct_task=${candidate} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc} direct_claim_rc=${direct_claim_rc}"
    exit 0
  fi
done

write_state 1 "create_and_claim" "failed" "planner_claim_after_create_failed" "${direct_claim_task}" "planner_claim_after_create_failed_hard" "create_rc=${create_rc};sync_rc=${sync_rc};collect_rc=${collect_rc};reconcile_rc=${reconcile_rc};sync_after_create_rc=${sync_after_create_rc};claim_rc=${claim_after_create_rc};source=${CREATE_SOURCE};wait_forbidden=${WAIT_FORBIDDEN}"
echo "PLANNER_AUTONOMY status=error action=create_and_claim outcome=failed issue=planner_claim_after_create_failed_hard batch_id=${created_batch_id} direct_task=${direct_claim_task} create_rc=${create_rc} sync_after_create_rc=${sync_after_create_rc} claim_rc=${claim_after_create_rc}"
exit 0
