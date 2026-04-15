#!/usr/bin/env bash
# admin_dispatcher_tick.sh
# Active dispatcher helper for admin lane (no new role).
# Non-blocking by default: all failures are soft unless explicitly requested.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "dispatch_result status=SOFT_FAIL reason=workspace_helper_missing"
  exit 0
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

STATE_DIR="${FC_ADMIN_DISPATCH_STATE_DIR:-${HOME}/.openclaw/cron/admin-dispatch}"
ROLE_STATE_DIR="${FC_ROLE_STATE_DIR:-${TMUX_ROLE_STATE_DIR:-${HOME}/.openclaw/cron/role-state}}"
LOG_FILE="${FC_ADMIN_DISPATCH_LOG_FILE:-${ROOT}/logs-codex-runs/fc-ticks/admin.dispatch.log}"
LOCK_FILE="${STATE_DIR}/dispatch.lock"
LAST_ACTION_FILE="${STATE_DIR}/last_action_epoch"
LAST_FINGERPRINT_FILE="${STATE_DIR}/last_ready_fingerprint"
TAKEOVER_ACTIVE_FILE="${STATE_DIR}/tshape_takeover_active"
TAKEOVER_ROLES_FILE="${STATE_DIR}/tshape_takeover_roles"
LAST_PLATEAU_ACTION_FILE="${STATE_DIR}/last_dependency_plateau_epoch"
LAST_PLATEAU_FINGERPRINT_FILE="${STATE_DIR}/last_dependency_plateau_fingerprint"
ADMIN_AUTONOMY_STATE_FILE="${FC_ADMIN_AUTONOMY_STATE_FILE:-${ROLE_STATE_DIR}/admin_autonomy_state.json}"

QUEUE_FILE="${FC_ADMIN_DISPATCH_QUEUE_FILE:-${ROOT}/logs-codex-runs/orchestrator-state/priority-queue.json}"
BOARD_FILE="${FC_ADMIN_DISPATCH_BOARD_FILE:-${ROOT}/logs-codex-runs/orchestrator-state/parallel-workstreams.json}"
EXEC_FILE="${FC_ADMIN_DISPATCH_EXEC_FILE:-${ROOT}/logs-codex-runs/orchestrator-state/executors-monitoring-latest.json}"
TICK_LOG_FILE="${FC_ADMIN_DISPATCH_TICK_LOG:-}"

DISPATCH_ENABLED="${FC_ADMIN_DISPATCH_ENABLED:-1}"
DISPATCH_DRY_RUN="${FC_ADMIN_DISPATCH_DRY_RUN:-0}"
DISPATCH_SOFT_FAIL="${FC_ADMIN_DISPATCH_SOFT_FAIL:-1}"
DISPATCH_COOLDOWN_SECONDS="${FC_ADMIN_DISPATCH_COOLDOWN_SECONDS:-300}"
DISPATCH_MAX_ACTIONS="${FC_ADMIN_DISPATCH_MAX_ACTIONS:-1}"
DISPATCH_SYNC_PRIORITY="${FC_ADMIN_DISPATCH_SYNC_PRIORITY:-1}"
DISPATCH_BYPASS_COOLDOWN_ON_HANDOFF="${FC_ADMIN_DISPATCH_BYPASS_COOLDOWN_ON_HANDOFF:-1}"
DISPATCH_BYPASS_COOLDOWN_ON_PLATEAU="${FC_ADMIN_DISPATCH_BYPASS_COOLDOWN_ON_PLATEAU:-1}"
DISPATCH_FORCE_ROLE_TICK="${FC_ADMIN_DISPATCH_FORCE_ROLE_TICK:-0}"
TSHAPE_MODE="${FC_ADMIN_TSHAPE_MODE:-full_takeover}"
TSHAPE_ACTIVATE_ON_FIRST_BLOCKED="${FC_ADMIN_TSHAPE_ACTIVATE_ON_FIRST_BLOCKED:-1}"
TSHAPE_UNTIL_RESOLUTION="${FC_ADMIN_TSHAPE_UNTIL_RESOLUTION:-1}"
DISPATCH_DEP_FUNNEL_ENABLED="${FC_ADMIN_DISPATCH_DEP_FUNNEL_ENABLED:-1}"
DISPATCH_DEP_FUNNEL_WAITING_DEP_THRESHOLD="${FC_ADMIN_DISPATCH_DEP_FUNNEL_WAITING_DEP_THRESHOLD:-10}"
DISPATCH_DEP_FUNNEL_READY_MAX="${FC_ADMIN_DISPATCH_DEP_FUNNEL_READY_MAX:-1}"
DISPATCH_DEP_FUNNEL_IN_PROGRESS_MAX="${FC_ADMIN_DISPATCH_DEP_FUNNEL_IN_PROGRESS_MAX:-2}"
DISPATCH_DEP_FUNNEL_COOLDOWN_SECONDS="${FC_ADMIN_DISPATCH_DEP_FUNNEL_COOLDOWN_SECONDS:-900}"
DISPATCH_DEP_FUNNEL_FORCE_ROLE="${FC_ADMIN_DISPATCH_DEP_FUNNEL_FORCE_ROLE:-planner}"
DISPATCH_DEP_FUNNEL_FORCE_ROLE_TICK="${FC_ADMIN_DISPATCH_DEP_FUNNEL_FORCE_ROLE_TICK:-1}"
DISPATCH_DEP_FUNNEL_FORCE_TICK_TIMEOUT_SECONDS="${FC_ADMIN_DISPATCH_DEP_FUNNEL_FORCE_TICK_TIMEOUT_SECONDS:-180}"
DISPATCH_DEP_FUNNEL_MESSAGE_TTL_MIN="${FC_ADMIN_DISPATCH_DEP_FUNNEL_MESSAGE_TTL_MIN:-240}"
AGENT_MESSAGE_BUS_ENABLED="${AGENT_MESSAGE_BUS_ENABLED:-1}"
AGENT_MESSAGE_BUS_SCRIPT="${AGENT_MESSAGE_BUS_SCRIPT:-${ROOT}/platform/automation/agent_message_bus.sh}"
FC_DEV_WIP_TARGET="${FC_DEV_WIP_TARGET:-2}"
FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S="${FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S:-600}"
DEV_LAST_CLAIM_FILE="${STATE_DIR}/last_dev_claim.json"

FC_ADMIN_AUTONOMY_ENABLED="${FC_ADMIN_AUTONOMY_ENABLED:-1}"
FC_ADMIN_STALL_TICKS_THRESHOLD="${FC_ADMIN_STALL_TICKS_THRESHOLD:-2}"
FC_ADMIN_AUTONOMY_SCOPE="${FC_ADMIN_AUTONOMY_SCOPE:-full_with_proofs}"
FC_ADMIN_AUTONOMY_MAX_ACTIONS="${FC_ADMIN_AUTONOMY_MAX_ACTIONS:-2}"
FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S="${FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S:-300}"
FC_ADMIN_AUTONOMY_RETRY_BACKOFF_S="${FC_ADMIN_AUTONOMY_RETRY_BACKOFF_S:-120}"
FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES="${FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES:-3}"
FC_ADMIN_PROOF_GATE_STRICT="${FC_ADMIN_PROOF_GATE_STRICT:-1}"
FC_ADMIN_AUTONOMY_SECURITY_WINDOW_MIN="${FC_ADMIN_AUTONOMY_SECURITY_WINDOW_MIN:-10}"

CHANGE_PLAN="${FC_ADMIN_DISPATCH_CHANGE_PLAN:-Definir le scope exact du module et du task cible; evaluer dependency impact amont aval et integration cross role; identifier les risques de regression et les edge cases critiques; executer verification via tests smoke pytest puis collecter les preuves; preparer un rollback fallback de mitigation si la validation echoue.}"
ARCH_CHECKS="${FC_ADMIN_DISPATCH_ARCH_CHECKS:-Reutiliser les modules existants et limiter le couplage inter composants; maintenir la stabilite des contrats API et schemas publics; conserver observabilite et plan de degradation sans breaking change.}"

mkdir -p "$STATE_DIR" "$ROLE_STATE_DIR" "$(dirname "$LOG_FILE")"

norm_int() {
  local raw="${1:-}"
  local fallback="$2"
  local min="$3"
  local max="$4"
  if ! [[ "$raw" =~ ^[0-9]+$ ]]; then
    echo "$fallback"
    return 0
  fi
  if (( raw < min )); then
    echo "$min"
    return 0
  fi
  if (( raw > max )); then
    echo "$max"
    return 0
  fi
  echo "$raw"
}

DISPATCH_COOLDOWN_SECONDS="$(norm_int "$DISPATCH_COOLDOWN_SECONDS" "300" "60" "7200")"
DISPATCH_MAX_ACTIONS="$(norm_int "$DISPATCH_MAX_ACTIONS" "1" "1" "5")"
DISPATCH_DEP_FUNNEL_WAITING_DEP_THRESHOLD="$(norm_int "$DISPATCH_DEP_FUNNEL_WAITING_DEP_THRESHOLD" "10" "1" "999")"
DISPATCH_DEP_FUNNEL_READY_MAX="$(norm_int "$DISPATCH_DEP_FUNNEL_READY_MAX" "1" "0" "50")"
DISPATCH_DEP_FUNNEL_IN_PROGRESS_MAX="$(norm_int "$DISPATCH_DEP_FUNNEL_IN_PROGRESS_MAX" "2" "0" "50")"
DISPATCH_DEP_FUNNEL_COOLDOWN_SECONDS="$(norm_int "$DISPATCH_DEP_FUNNEL_COOLDOWN_SECONDS" "900" "60" "86400")"
DISPATCH_DEP_FUNNEL_FORCE_TICK_TIMEOUT_SECONDS="$(norm_int "$DISPATCH_DEP_FUNNEL_FORCE_TICK_TIMEOUT_SECONDS" "180" "30" "900")"
DISPATCH_DEP_FUNNEL_MESSAGE_TTL_MIN="$(norm_int "$DISPATCH_DEP_FUNNEL_MESSAGE_TTL_MIN" "240" "15" "10080")"
FC_ADMIN_STALL_TICKS_THRESHOLD="$(norm_int "$FC_ADMIN_STALL_TICKS_THRESHOLD" "2" "2" "20")"
FC_ADMIN_AUTONOMY_MAX_ACTIONS="$(norm_int "$FC_ADMIN_AUTONOMY_MAX_ACTIONS" "2" "1" "5")"
FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S="$(norm_int "$FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S" "300" "30" "7200")"
FC_ADMIN_AUTONOMY_RETRY_BACKOFF_S="$(norm_int "$FC_ADMIN_AUTONOMY_RETRY_BACKOFF_S" "120" "30" "1800")"
FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES="$(norm_int "$FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES" "3" "1" "10")"
FC_ADMIN_AUTONOMY_SECURITY_WINDOW_MIN="$(norm_int "$FC_ADMIN_AUTONOMY_SECURITY_WINDOW_MIN" "10" "1" "120")"
FC_DEV_WIP_TARGET="$(norm_int "$FC_DEV_WIP_TARGET" "2" "1" "5")"
FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S="$(norm_int "$FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S" "600" "0" "7200")"
if [[ "$FC_ADMIN_AUTONOMY_ENABLED" == "1" ]]; then
  DISPATCH_MAX_ACTIONS="$FC_ADMIN_AUTONOMY_MAX_ACTIONS"
fi

case "$DISPATCH_DEP_FUNNEL_FORCE_ROLE" in
  planner|dev|admin) ;;
  *) DISPATCH_DEP_FUNNEL_FORCE_ROLE="planner" ;;
esac

ts_utc() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

log_line() {
  local raw="$1"
  local line
  line="$(printf '%s %s\n' "$(ts_utc)" "$raw")"
  printf '%s\n' "$line" >> "$LOG_FILE"
  if [[ -n "$TICK_LOG_FILE" ]]; then
    printf '%s [DISPATCH] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$(printf '%s' "$raw" | cut -c1-200)" >> "$TICK_LOG_FILE"
  fi
  printf '%s\n' "$raw"
}

decision() {
  log_line "dispatch_decision $*"
}

action() {
  log_line "dispatch_action $*"
}

result() {
  log_line "dispatch_result $*"
}

exit_soft() {
  local reason="$1"
  result "status=NOOP reason=${reason}"
  exit 0
}

run_cmd() {
  local label="$1"
  shift
  local out_file err_file rc
  out_file="$(mktemp)"
  err_file="$(mktemp)"
  set +e
  "$@" >"$out_file" 2>"$err_file"
  rc=$?
  set -e
  local out_tail err_tail
  out_tail="$(tail -n 1 "$out_file" 2>/dev/null | tr '\r' ' ' | cut -c1-140)"
  err_tail="$(tail -n 1 "$err_file" 2>/dev/null | tr '\r' ' ' | cut -c1-140)"
  rm -f "$out_file" "$err_file"
  if [[ "$rc" -eq 0 ]]; then
    action "name=${label} rc=0 out=${out_tail:-none}"
    return 0
  fi
  action "name=${label} rc=${rc} err=${err_tail:-none}"
  return 1
}

contract_file_for_role() {
  local role="$1"
  printf '%s\n' "${ROLE_STATE_DIR}/${role}.last_contract"
}

contract_field() {
  local role="$1"
  local key="$2"
  local f
  f="$(contract_file_for_role "$role")"
  [[ -f "$f" ]] || return 0
  sed -n "s/^${key}:[[:space:]]*//p" "$f" | head -n 1 | tr -d '\r' | sed 's/[[:space:]]*$//'
}

extract_evidence_value() {
  local evidence="$1"
  local key="$2"
  printf '%s\n' "$evidence" \
    | tr ';' '\n' \
    | sed -n "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*//Ip" \
    | head -n 1 \
    | sed 's/[[:space:]]*$//'
}

lane_in_progress_count() {
  local role="$1"
  jq -r --arg role "$role" '[.tasks[]? | select(((.role // .assigned_to // .assignee // "") == $role) and (.state // "") == "IN_PROGRESS")] | length' "$BOARD_FILE" 2>/dev/null || echo 0
}

lane_in_progress_task() {
  local role="$1"
  jq -r --arg role "$role" '
    [.tasks[]?
      | select(((.role // .assigned_to // .assignee // "") == $role) and (.state // "") == "IN_PROGRESS")
      | (.id // "")
    ] | map(select(length>0)) | .[0] // ""
  ' "$BOARD_FILE" 2>/dev/null || true
}

lane_ready_task() {
  local role="$1"
  local ready_states_json='["READY"]'
  case "$role" in
    admin)
      ready_states_json='["READY","READY_PLANNER","READY_ADMIN"]'
      ;;
    dev)
      ready_states_json='["READY","READY_DEV"]'
      ;;
    planner)
      ready_states_json='["READY","READY_PLANNER"]'
      ;;
  esac
  jq -r --arg role "$role" --argjson ready_states "$ready_states_json" '
    [.tasks[]?
      | select(((.role // .assigned_to // .assignee // "") == $role))
      | select((.state // "") as $state | ($ready_states | index($state)) != null)
      | select(((.assignee // "") | length) == 0 or .assignee == $role)
      | (.id // "")
    ] | map(select(length>0)) | .[0] // ""
  ' "$BOARD_FILE" 2>/dev/null || true
}

fairness_pick_ready_task() {
  local role="$1"
  python3 - "$BOARD_FILE" "$ADMIN_AUTONOMY_STATE_FILE" "$role" <<'PY'
import json
import sys
from pathlib import Path

board_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
role = str(sys.argv[3] or "").strip()
if not role:
    print("\t0")
    raise SystemExit(0)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default


board = _load_json(board_path, {})
if not isinstance(board, dict):
    board = {}

ready_tasks: list[str] = []
for task in board.get("tasks", []) or []:
    if not isinstance(task, dict):
        continue
    if str(task.get("role", "")).strip() != role:
        continue
    if str(task.get("state", "")).strip().upper() != "READY":
        continue
    assignee = str(task.get("assignee", "")).strip()
    if assignee and assignee != role:
        continue
    task_id = str(task.get("id", "")).strip()
    if task_id:
        ready_tasks.append(task_id)

ready_tasks = sorted(dict.fromkeys(ready_tasks))
if not ready_tasks:
    print("\t0")
    raise SystemExit(0)

state = _load_json(state_path, {})
if not isinstance(state, dict):
    state = {}
fairness = state.get("dispatch_fairness_cursor")
if not isinstance(fairness, dict):
    fairness = {}
raw_cursor = fairness.get(role, 0)
try:
    cursor = int(raw_cursor)
except Exception:
    cursor = 0
if cursor < 0:
    cursor = 0

idx = cursor % len(ready_tasks)
slot = idx + 1
selected = ready_tasks[idx]
fairness[role] = (idx + 1) % len(ready_tasks)
state["dispatch_fairness_cursor"] = fairness
state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(f"{selected}\t{slot}")
PY
}

read_admin_autonomy_json() {
  local expr="$1"
  if [[ ! -f "$ADMIN_AUTONOMY_STATE_FILE" ]]; then
    echo ""
    return 0
  fi
  jq -r "${expr} // empty" "$ADMIN_AUTONOMY_STATE_FILE" 2>/dev/null || true
}

role_has_fresh_critical_issue() {
  local role="$1"
  local window_min="$2"
  local issue_file="${ROOT}/logs-codex-runs/orchestrator-state/agent-iteration-issues.jsonl"
  python3 - "$issue_file" "$role" "$window_min" <<'PY' 2>/dev/null || echo 0
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

path = Path(sys.argv[1])
role = str(sys.argv[2] or "").strip().lower()
try:
    window_min = int(str(sys.argv[3] or "10").strip())
except Exception:
    window_min = 10
if window_min < 1:
    window_min = 1
if not role or not path.exists():
    print("0")
    raise SystemExit(0)

cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_min)

def parse_ts(raw: str):
    raw = str(raw or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

for line in reversed(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-1500:]):
    line = line.strip()
    if not line:
        continue
    try:
        row = json.loads(line)
    except Exception:
        continue
    if str(row.get("role", "")).strip().lower() != role:
        continue
    ts = parse_ts(row.get("ts_utc", ""))
    if ts is None or ts < cutoff:
        continue
    if str(row.get("max_severity", "")).strip().upper() == "CRITICAL":
        print("1")
        raise SystemExit(0)
print("0")
PY
}

autonomy_action_allowed() {
  local role="$1"
  local task="$2"
  local action_type="$3"
  local key="${role}|${task:-none}|${action_type}"
  local next_epoch
  local failures
  next_epoch="$(read_admin_autonomy_json ".cooldown_by_role.\"${key}\".next_epoch")"
  failures="$(read_admin_autonomy_json ".cooldown_by_role.\"${key}\".failures")"
  [[ "$next_epoch" =~ ^[0-9]+$ ]] || next_epoch=0
  [[ "$failures" =~ ^[0-9]+$ ]] || failures=0
  if (( failures >= FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES )); then
    AUTO_NEEDS_HUMAN_REVIEW["$role"]=1
    decision "autonomy_loop_guard role=${role} task=${task:-none} action=${action_type} failures=${failures}"
    return 1
  fi
  if (( now_epoch < next_epoch )); then
    decision "autonomy_cooldown role=${role} task=${task:-none} action=${action_type} next_epoch=${next_epoch}"
    return 1
  fi
  return 0
}

autonomy_record_action_outcome() {
  local role="$1"
  local task="$2"
  local action_type="$3"
  local success="$4"
  local key="${role}|${task:-none}|${action_type}"
  local prev_fail
  local fail_count
  local next_epoch
  prev_fail="$(read_admin_autonomy_json ".cooldown_by_role.\"${key}\".failures")"
  [[ "$prev_fail" =~ ^[0-9]+$ ]] || prev_fail=0
  if [[ "$success" == "1" ]]; then
    fail_count=0
    next_epoch=$(( now_epoch + FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S ))
  else
    fail_count=$(( prev_fail + 1 ))
    if (( fail_count >= 2 )); then
      local backoff=$(( FC_ADMIN_AUTONOMY_RETRY_BACKOFF_S * (2 ** (fail_count - 2)) ))
      next_epoch=$(( now_epoch + backoff ))
    else
      next_epoch=$(( now_epoch + FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S ))
    fi
    if (( fail_count >= FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES )); then
      AUTO_NEEDS_HUMAN_REVIEW["$role"]=1
    fi
  fi
  python3 - "$ADMIN_AUTONOMY_STATE_FILE" "$key" "$next_epoch" "$fail_count" <<'PY' >/dev/null 2>&1 || true
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = str(sys.argv[2])
next_epoch = int(str(sys.argv[3] or "0"))
failures = int(str(sys.argv[4] or "0"))
payload = {}
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        payload = {}
if not isinstance(payload, dict):
    payload = {}
cooldowns = payload.get("cooldown_by_role")
if not isinstance(cooldowns, dict):
    cooldowns = {}
cooldowns[key] = {"next_epoch": next_epoch, "failures": failures}
payload["cooldown_by_role"] = cooldowns
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
}

persist_autonomy_state() {
  local blocked_roles_csv_in="$1"
  local virtual_roles_csv_in="$2"
  python3 - \
    "$ADMIN_AUTONOMY_STATE_FILE" \
    "$AUTO_ACTIVE" \
    "$AUTO_TRIGGER" \
    "$AUTO_TARGET_ROLE" \
    "$AUTO_TARGET_TASK" \
    "$AUTO_REASON_BLOCKER" \
    "$AUTO_LAST_ACTION" \
    "$AUTO_LAST_OUTCOME" \
    "$AUTO_ACTION_SEQ" \
    "$AUTO_SINCE_TS" \
    "$blocked_roles_csv_in" \
    "$virtual_roles_csv_in" \
    "${AUTO_STREAK_BY_ROLE[planner]:-0}" \
    "${AUTO_STREAK_BY_ROLE[dev]:-0}" \
    "${AUTO_LAST_TASK_BY_ROLE[planner]:-}" \
    "${AUTO_LAST_TASK_BY_ROLE[dev]:-}" \
    "${AUTO_LAST_ACTION_BY_ROLE[planner]:-}" \
    "${AUTO_LAST_ACTION_BY_ROLE[dev]:-}" \
    "${AUTO_NEEDS_HUMAN_REVIEW[planner]:-0}" \
    "${AUTO_NEEDS_HUMAN_REVIEW[dev]:-0}" <<'PY' >/dev/null 2>&1 || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
active = str(sys.argv[2] or "0") == "1"
trigger = str(sys.argv[3] or "none").strip() or "none"
target_role = str(sys.argv[4] or "").strip()
target_task = str(sys.argv[5] or "").strip()
reason = str(sys.argv[6] or "NONE").strip() or "NONE"
last_action = str(sys.argv[7] or "idle").strip() or "idle"
last_outcome = str(sys.argv[8] or "none").strip() or "none"
action_seq = str(sys.argv[9] or "").strip()
since_ts = str(sys.argv[10] or "").strip()
blocked_roles = [x for x in str(sys.argv[11] or "").split(",") if x]
virtual_blocked_roles = [x for x in str(sys.argv[12] or "").split(",") if x]
streak_planner = int(str(sys.argv[13] or "0") or "0")
streak_dev = int(str(sys.argv[14] or "0") or "0")
last_task_planner = str(sys.argv[15] or "").strip()
last_task_dev = str(sys.argv[16] or "").strip()
last_action_planner = str(sys.argv[17] or "").strip()
last_action_dev = str(sys.argv[18] or "").strip()
needs_planner = str(sys.argv[19] or "0") == "1"
needs_dev = str(sys.argv[20] or "0") == "1"

payload = {}
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        payload = {}
if not isinstance(payload, dict):
    payload = {}
now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
if active and not since_ts:
    since_ts = now_ts
payload.update(
    {
        "active": active,
        "trigger": trigger,
        "target_role": target_role,
        "target_task": target_task,
        "reason_blocker": reason,
        "last_action": last_action,
        "last_outcome": last_outcome,
        "last_action_seq": action_seq,
        "since_ts": since_ts,
        "resolved": not active,
        "blocked_roles": blocked_roles,
        "virtual_blocked_roles": virtual_blocked_roles,
        "streak_by_role": {"planner": streak_planner, "dev": streak_dev},
        "last_task_by_role": {"planner": last_task_planner, "dev": last_task_dev},
        "last_action_by_role": {"planner": last_action_planner, "dev": last_action_dev},
        "needs_human_review_by_role": {"planner": needs_planner, "dev": needs_dev},
        "scope": "full_with_proofs",
        "updated_at": now_ts,
    }
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
}

declare -A AUTO_STREAK_BY_ROLE AUTO_LAST_TASK_BY_ROLE AUTO_LAST_ACTION_BY_ROLE AUTO_NEEDS_HUMAN_REVIEW
AUTO_ACTIVE=0
AUTO_TRIGGER="none"
AUTO_TARGET_ROLE=""
AUTO_TARGET_TASK=""
AUTO_REASON_BLOCKER="NONE"
AUTO_LAST_ACTION="idle"
AUTO_LAST_OUTCOME="none"
AUTO_ACTION_SEQ=""
AUTO_SINCE_TS=""
for _role in planner dev; do
  AUTO_STREAK_BY_ROLE["$_role"]="$(read_admin_autonomy_json ".streak_by_role.${_role}")"
  AUTO_LAST_TASK_BY_ROLE["$_role"]="$(read_admin_autonomy_json ".last_task_by_role.${_role}")"
  AUTO_LAST_ACTION_BY_ROLE["$_role"]="$(read_admin_autonomy_json ".last_action_by_role.${_role}")"
  AUTO_NEEDS_HUMAN_REVIEW["$_role"]="$(read_admin_autonomy_json ".needs_human_review_by_role.${_role}")"
  [[ "${AUTO_STREAK_BY_ROLE[$_role]:-}" =~ ^[0-9]+$ ]] || AUTO_STREAK_BY_ROLE["$_role"]=0
  [[ "${AUTO_NEEDS_HUMAN_REVIEW[$_role]:-}" =~ ^[01]$ ]] || AUTO_NEEDS_HUMAN_REVIEW["$_role"]=0
done
auto_active_raw="$(read_admin_autonomy_json ".active")"
if [[ "$auto_active_raw" == "true" || "$auto_active_raw" == "1" ]]; then
  AUTO_ACTIVE=1
fi
AUTO_TRIGGER="$(read_admin_autonomy_json ".trigger")"
AUTO_TARGET_ROLE="$(read_admin_autonomy_json ".target_role")"
AUTO_TARGET_TASK="$(read_admin_autonomy_json ".target_task")"
AUTO_REASON_BLOCKER="$(read_admin_autonomy_json ".reason_blocker")"
AUTO_LAST_ACTION="$(read_admin_autonomy_json ".last_action")"
AUTO_LAST_OUTCOME="$(read_admin_autonomy_json ".last_outcome")"
AUTO_ACTION_SEQ="$(read_admin_autonomy_json ".last_action_seq")"
AUTO_SINCE_TS="$(read_admin_autonomy_json ".since_ts")"
[[ -n "$AUTO_TRIGGER" ]] || AUTO_TRIGGER="none"
[[ -n "$AUTO_REASON_BLOCKER" ]] || AUTO_REASON_BLOCKER="NONE"

if [[ "$DISPATCH_ENABLED" != "1" ]]; then
  exit_soft "disabled"
fi

if [[ ! -f "$QUEUE_FILE" || ! -f "$BOARD_FILE" ]]; then
  if [[ "$DISPATCH_SOFT_FAIL" == "1" ]]; then
    result "status=SOFT_FAIL reason=missing_queue_or_board queue=${QUEUE_FILE} board=${BOARD_FILE}"
    exit 0
  fi
  result "status=BLOCKED reason=missing_queue_or_board queue=${QUEUE_FILE} board=${BOARD_FILE}"
  exit 1
fi

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    exit_soft "locked"
  fi
fi

blocked_roles_all_csv=""
blocked_roles_csv=""
blocked_count=0
if [[ -f "$EXEC_FILE" ]]; then
  blocked_roles_all_csv="$(jq -r '
    (
      [.summary.blocker_roles[]? | strings | select(length>0)]
      +
      [.roles | to_entries[]? | select(((.value.blocker_id // "NONE") | tostring | ascii_upcase) != "NONE") | (.key // "")]
    )
    | map(select(test("^(planner|dev|admin)$")))
    | unique
    | join(",")
  ' "$EXEC_FILE" 2>/dev/null || true)"
fi
if [[ -n "$blocked_roles_all_csv" ]]; then
  blocked_roles_csv="$(
    {
      printf '%s\n' "$blocked_roles_all_csv" \
        | tr ',' '\n' \
        | sed '/^$/d' \
        | rg '^(planner|dev|admin)$' \
        | paste -sd ',' -;
    } || true
  )"
fi
if [[ -n "$blocked_roles_csv" ]]; then
  blocked_count="$(printf '%s\n' "$blocked_roles_csv" | tr ',' '\n' | sed '/^$/d' | wc -l | tr -d ' ')"
fi

now_epoch="$(date +%s)"
last_action_epoch="$(cat "$LAST_ACTION_FILE" 2>/dev/null || echo 0)"
if ! [[ "$last_action_epoch" =~ ^[0-9]+$ ]]; then
  last_action_epoch=0
fi
cooldown_left=0
if (( now_epoch - last_action_epoch < DISPATCH_COOLDOWN_SECONDS )); then
  cooldown_left=$(( DISPATCH_COOLDOWN_SECONDS - (now_epoch - last_action_epoch) ))
fi

ready_queue_count="$(jq '[.items[]? | select((.state // "")=="READY")] | length' "$QUEUE_FILE" 2>/dev/null || echo 0)"
queue_waiting_dep_count="$(jq '[.items[]? | select((.state // "")=="WAITING_DEP")] | length' "$QUEUE_FILE" 2>/dev/null || echo 0)"
queue_in_progress_count="$(jq '[.items[]? | select((.state // "")=="IN_PROGRESS")] | length' "$QUEUE_FILE" 2>/dev/null || echo 0)"
planner_in_progress_count="$(jq '[.tasks[]? | select((.role // "")=="planner" and (.state // "")=="IN_PROGRESS")] | length' "$BOARD_FILE" 2>/dev/null || echo 0)"
dev_in_progress_count="$(jq '[.tasks[]? | select((.role // "")=="dev" and (.state // "")=="IN_PROGRESS")] | length' "$BOARD_FILE" 2>/dev/null || echo 0)"
admin_in_progress_count="$(jq '[.tasks[]? | select((.role // "")=="admin" and (.state // "")=="IN_PROGRESS")] | length' "$BOARD_FILE" 2>/dev/null || echo 0)"
board_waiting_dep_count="$(jq '[.tasks[]? | select((.state // "")=="WAITING_DEP")] | length' "$BOARD_FILE" 2>/dev/null || echo 0)"
board_in_progress_count="$(jq '[.tasks[]? | select((.state // "")=="IN_PROGRESS")] | length' "$BOARD_FILE" 2>/dev/null || echo 0)"
planner_in_progress_tasks_csv="$(
  jq -r '[.tasks[]? | select((.role // "")=="planner" and (.state // "")=="IN_PROGRESS") | (.id // "")] | map(select(length>0)) | join(",")' "$BOARD_FILE" 2>/dev/null || true
)"
open_handoff_count="$(jq '[.handoffs[]? | select(((.status // "") | ascii_upcase)=="OPEN" and ((.to_role // "") | test("^(planner|dev|admin)$"))] | length' "$BOARD_FILE" 2>/dev/null || echo 0)"

plateau_detected=0
if [[ "$DISPATCH_DEP_FUNNEL_ENABLED" == "1" ]] \
  && (( queue_waiting_dep_count >= DISPATCH_DEP_FUNNEL_WAITING_DEP_THRESHOLD )) \
  && (( ready_queue_count <= DISPATCH_DEP_FUNNEL_READY_MAX )) \
  && (( queue_in_progress_count <= DISPATCH_DEP_FUNNEL_IN_PROGRESS_MAX )) \
  && (( planner_in_progress_count > 0 )); then
  plateau_detected=1
fi

declare -a explicit_blocked_roles_arr=() virtual_blocked_roles_arr=() takeover_roles_arr=()
virtual_blocked_roles_csv=""
for role in planner dev admin; do
  lane_count="$(lane_in_progress_count "$role")"
  [[ "$lane_count" =~ ^[0-9]+$ ]] || lane_count=0
  lane_active=0
  if (( lane_count > 0 )); then
    lane_active=1
  fi
  role_delta_u="$(printf '%s' "$(contract_field "$role" "DELTA")" | tr '[:lower:]' '[:upper:]' | tr -d '[:space:]')"
  evidence_raw="$(contract_field "$role" "EVIDENCE")"
  evidence_task_id="$(extract_evidence_value "$evidence_raw" "task_id")"
  evidence_stream_id="$(extract_evidence_value "$evidence_raw" "stream_id")"
  if [[ -z "$evidence_task_id" ]]; then
    evidence_task_id="$(lane_in_progress_task "$role")"
  fi
  if [[ -z "$evidence_stream_id" && "$evidence_task_id" == BATCH-* ]]; then
    evidence_stream_id="${evidence_task_id%-*}"
  fi
  task_sig="${evidence_task_id:-none}|${evidence_stream_id:-none}"
  prev_task_sig="${AUTO_LAST_TASK_BY_ROLE[$role]:-}"
  stale_signal=0
  case "$role_delta_u" in
    NO_DELTA|NONE_NO_SIGNAL|LOCK_SKIP)
      stale_signal=1
      ;;
  esac
  if [[ "$lane_active" == "1" && "$stale_signal" == "1" ]]; then
    if [[ -n "$prev_task_sig" && "$prev_task_sig" == "$task_sig" ]]; then
      AUTO_STREAK_BY_ROLE["$role"]=$(( ${AUTO_STREAK_BY_ROLE[$role]:-0} + 1 ))
    else
      AUTO_STREAK_BY_ROLE["$role"]=1
    fi
  else
    AUTO_STREAK_BY_ROLE["$role"]=0
  fi
  AUTO_LAST_TASK_BY_ROLE["$role"]="$task_sig"
  if (( ${AUTO_STREAK_BY_ROLE[$role]:-0} >= FC_ADMIN_STALL_TICKS_THRESHOLD )) && [[ "$lane_active" == "1" && "$stale_signal" == "1" ]]; then
    virtual_blocked_roles_arr+=("$role")
  fi
done
if (( ${#virtual_blocked_roles_arr[@]} > 0 )); then
  virtual_blocked_roles_csv="$(printf '%s\n' "${virtual_blocked_roles_arr[@]}" | sort -u | paste -sd ',' -)"
fi

if [[ -n "$blocked_roles_csv" ]]; then
  IFS=',' read -r -a explicit_blocked_roles_arr <<< "$blocked_roles_csv"
fi

actionable_blocked_roles_csv=""
declare -a actionable_blocked_roles_arr=()
if (( ${#explicit_blocked_roles_arr[@]} > 0 )); then
  for role in "${explicit_blocked_roles_arr[@]}"; do
    role="$(printf '%s' "$role" | tr -d '[:space:]')"
    [[ "$role" == "planner" || "$role" == "dev" || "$role" == "admin" ]] || continue
    actionable_blocked_roles_arr+=("$role")
  done
  if (( ${#actionable_blocked_roles_arr[@]} > 0 )); then
    actionable_blocked_roles_csv="$(printf '%s\n' "${actionable_blocked_roles_arr[@]}" | sort -u | paste -sd ',' -)"
  fi
fi

AUTO_TRIGGER="none"
AUTO_TARGET_ROLE=""
AUTO_TARGET_TASK=""
AUTO_REASON_BLOCKER="NONE"
AUTONOMY_REASON_CODE="NO_BLOCKED_ROLES"
if [[ "$FC_ADMIN_AUTONOMY_ENABLED" == "1" ]]; then
  if (( ${#actionable_blocked_roles_arr[@]} > 0 )); then
    AUTO_TRIGGER="blocked_explicit"
    AUTONOMY_REASON_CODE="ACTIONABLE_BLOCKED_ROLES"
    for role in "${actionable_blocked_roles_arr[@]}"; do
      role="$(printf '%s' "$role" | tr -d '[:space:]')"
      [[ "$role" == "planner" || "$role" == "dev" || "$role" == "admin" ]] || continue
      AUTO_TARGET_ROLE="$role"
      AUTO_REASON_BLOCKER="BLOCKED_RUNTIME"
      break
    done
  elif [[ -n "$blocked_roles_all_csv" ]]; then
    AUTONOMY_REASON_CODE="ADMIN_ONLY_BLOCK"
  fi
  if [[ "$AUTO_TRIGGER" == "none" && ${#virtual_blocked_roles_arr[@]} -gt 0 ]]; then
    AUTO_TRIGGER="stalled_lane"
    AUTONOMY_REASON_CODE="VIRTUAL_BLOCKED_ROLES"
    best_role=""
    best_streak=0
    for role in "${virtual_blocked_roles_arr[@]}"; do
      streak_now="${AUTO_STREAK_BY_ROLE[$role]:-0}"
      if (( streak_now >= best_streak )); then
        best_streak="$streak_now"
        best_role="$role"
      fi
    done
    AUTO_TARGET_ROLE="$best_role"
    AUTO_REASON_BLOCKER="STALLED_LANE"
  fi
  if [[ "$AUTO_TRIGGER" == "none" && "$plateau_detected" == "1" ]]; then
    AUTO_TRIGGER="dependency_plateau"
    AUTONOMY_REASON_CODE="DEPENDENCY_PLATEAU"
    AUTO_TARGET_ROLE="${DISPATCH_DEP_FUNNEL_FORCE_ROLE}"
    AUTO_REASON_BLOCKER="DEPENDENCY_PLATEAU"
  fi
elif (( ${#actionable_blocked_roles_arr[@]} > 0 )); then
  AUTO_TRIGGER="blocked_explicit"
  AUTONOMY_REASON_CODE="ACTIONABLE_BLOCKED_ROLES"
  for role in "${actionable_blocked_roles_arr[@]}"; do
    role="$(printf '%s' "$role" | tr -d '[:space:]')"
    [[ "$role" == "planner" || "$role" == "dev" || "$role" == "admin" ]] || continue
    AUTO_TARGET_ROLE="$role"
    AUTO_REASON_BLOCKER="BLOCKED_RUNTIME"
    break
  done
elif [[ -n "$blocked_roles_all_csv" ]]; then
  AUTONOMY_REASON_CODE="ADMIN_ONLY_BLOCK"
fi
if [[ -n "$AUTO_TARGET_ROLE" ]]; then
  AUTO_TARGET_TASK="$(lane_in_progress_task "$AUTO_TARGET_ROLE")"
fi

takeover_active=0
if [[ "$AUTO_TRIGGER" != "none" ]]; then
  takeover_active=1
  AUTO_ACTIVE=1
  if [[ -z "$AUTO_SINCE_TS" || "$AUTO_TRIGGER" != "$(read_admin_autonomy_json ".trigger")" || "$AUTO_TARGET_ROLE" != "$(read_admin_autonomy_json ".target_role")" ]]; then
    AUTO_SINCE_TS="$(ts_utc)"
  fi
  takeover_roles_arr=()
  if [[ -n "$AUTO_TARGET_ROLE" ]]; then
    takeover_roles_arr+=("$AUTO_TARGET_ROLE")
  fi
  if [[ "$AUTO_TRIGGER" == "blocked_explicit" && ${#actionable_blocked_roles_arr[@]} -gt 0 ]]; then
    for role in "${actionable_blocked_roles_arr[@]}"; do
      role="$(printf '%s' "$role" | tr -d '[:space:]')"
      [[ "$role" == "planner" || "$role" == "dev" || "$role" == "admin" ]] || continue
      takeover_roles_arr+=("$role")
    done
  fi
else
  AUTO_ACTIVE=0
  AUTO_SINCE_TS=""
fi

if (( ${#takeover_roles_arr[@]} > 0 )); then
  blocked_roles_csv="$(printf '%s\n' "${takeover_roles_arr[@]}" | sort -u | paste -sd ',' -)"
else
  blocked_roles_csv=""
fi
if [[ -n "$blocked_roles_csv" ]]; then
  blocked_count="$(printf '%s\n' "$blocked_roles_csv" | tr ',' '\n' | sed '/^$/d' | wc -l | tr -d ' ')"
else
  blocked_count=0
fi
printf '%s\n' "$takeover_active" > "$TAKEOVER_ACTIVE_FILE"
if [[ "$takeover_active" == "1" ]]; then
  printf '%s\n' "${blocked_roles_csv:-none}" > "$TAKEOVER_ROLES_FILE"
else
  rm -f "$TAKEOVER_ROLES_FILE" >/dev/null 2>&1 || true
fi

decision "ready_queue=${ready_queue_count} queue_waiting_dep=${queue_waiting_dep_count} queue_in_progress=${queue_in_progress_count} board_waiting_dep=${board_waiting_dep_count} board_in_progress=${board_in_progress_count} planner_in_progress=${planner_in_progress_count} dev_in_progress=${dev_in_progress_count} admin_in_progress=${admin_in_progress_count} open_handoffs=${open_handoff_count} blocked_roles=${blocked_roles_csv:-none} actionable_blocked_roles=${actionable_blocked_roles_csv:-none} blocked_roles_all=${blocked_roles_all_csv:-none} virtual_blocked_roles=${virtual_blocked_roles_csv:-none} autonomy_trigger=${AUTO_TRIGGER} autonomy_reason_code=${AUTONOMY_REASON_CODE} autonomy_target=${AUTO_TARGET_ROLE:-none} autonomy_task=${AUTO_TARGET_TASK:-none} takeover_active=${takeover_active} dependency_funnel_plateau=${plateau_detected} tshape_mode=${TSHAPE_MODE} cooldown_left_s=${cooldown_left} max_actions=${DISPATCH_MAX_ACTIONS} dry_run=${DISPATCH_DRY_RUN}"

if (( cooldown_left > 0 )) && [[ "$takeover_active" != "1" ]] && ! { [[ "$DISPATCH_BYPASS_COOLDOWN_ON_HANDOFF" == "1" ]] && (( open_handoff_count > 0 )); } && ! { [[ "$DISPATCH_BYPASS_COOLDOWN_ON_PLATEAU" == "1" ]] && (( plateau_detected == 1 )); }; then
  AUTO_LAST_ACTION="cooldown"
  AUTO_LAST_OUTCOME="deferred"
  persist_autonomy_state "${blocked_roles_csv:-}" "${virtual_blocked_roles_csv:-}"
  result "status=NOOP reason=cooldown_active_${cooldown_left}s autonomy_trigger=${AUTO_TRIGGER} autonomy_reason_code=${AUTONOMY_REASON_CODE} autonomy_target=${AUTO_TARGET_ROLE:-none} autonomy_outcome=deferred dispatch_reason_code=COOLDOWN_ACTIVE stream_fairness_slot=0"
  exit 0
fi

actions_taken=0
DISPATCH_REASON_CODE="NO_ACTION"
DISPATCH_FAIRNESS_SLOT=0

# 0) T-shape full takeover: immediate on first blocked, stays active until resolution.
if [[ "$TSHAPE_MODE" == "full_takeover" && "$takeover_active" == "1" && "$blocked_count" -gt 0 ]]; then
  AUTO_LAST_ACTION="takeover_active"
  AUTO_LAST_OUTCOME="partial"
  AUTO_ACTION_SEQ=""
  auto_sync_done=0
  IFS=',' read -r -a blocked_roles_arr <<< "$blocked_roles_csv"
  for blocked_role in "${blocked_roles_arr[@]}"; do
    blocked_role="$(printf '%s' "$blocked_role" | tr -d '[:space:]')"
    [[ -z "$blocked_role" ]] && continue
    [[ "$blocked_role" == "planner" || "$blocked_role" == "dev" || "$blocked_role" == "admin" ]] || continue
    AUTO_TARGET_ROLE="$blocked_role"
    if (( actions_taken >= DISPATCH_MAX_ACTIONS )); then
      break
    fi

    if [[ "$auto_sync_done" == "0" ]] && (( actions_taken < DISPATCH_MAX_ACTIONS )) && [[ "$DISPATCH_SYNC_PRIORITY" == "1" ]] && autonomy_action_allowed "$blocked_role" "${AUTO_TARGET_TASK:-none}" "sync"; then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=autonomy_sync_priority dry_run=1 role=${blocked_role}"
        actions_taken=$((actions_taken + 1))
        auto_sync_done=1
        AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}sync"
        autonomy_record_action_outcome "$blocked_role" "${AUTO_TARGET_TASK:-none}" "sync" "1"
      else
        if run_cmd "autonomy_sync_priority" python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board "$BOARD_FILE" --queue "$QUEUE_FILE"; then
          actions_taken=$((actions_taken + 1))
          auto_sync_done=1
          AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}sync"
          autonomy_record_action_outcome "$blocked_role" "${AUTO_TARGET_TASK:-none}" "sync" "1"
        else
          autonomy_record_action_outcome "$blocked_role" "${AUTO_TARGET_TASK:-none}" "sync" "0"
        fi
      fi
    fi

    # Full takeover first action: force immediate tick of blocked lane.
    if (( actions_taken < DISPATCH_MAX_ACTIONS )) && autonomy_action_allowed "$blocked_role" "${AUTO_TARGET_TASK:-none}" "force_tick"; then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=tshape_force_role_tick dry_run=1 role=${blocked_role}"
        actions_taken=$((actions_taken + 1))
        AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}force_tick"
        autonomy_record_action_outcome "$blocked_role" "${AUTO_TARGET_TASK:-none}" "force_tick" "1"
      else
        if run_cmd "tshape_force_role_tick" bash scripts/fc_agent_tick.sh "$blocked_role"; then
          actions_taken=$((actions_taken + 1))
          AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}force_tick"
          autonomy_record_action_outcome "$blocked_role" "${AUTO_TARGET_TASK:-none}" "force_tick" "1"
        else
          autonomy_record_action_outcome "$blocked_role" "${AUTO_TARGET_TASK:-none}" "force_tick" "0"
        fi
      fi
    fi

    if (( actions_taken < DISPATCH_MAX_ACTIONS )); then
      blocked_ready_task="$(lane_ready_task "$blocked_role")"
      if [[ -n "$blocked_ready_task" ]] && autonomy_action_allowed "$blocked_role" "$blocked_ready_task" "claim"; then
        if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
          action "name=tshape_claim_ready dry_run=1 role=${blocked_role} task=${blocked_ready_task}"
          actions_taken=$((actions_taken + 1))
          AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}claim"
          AUTO_TARGET_TASK="$blocked_ready_task"
          AUTO_LAST_ACTION_BY_ROLE["$blocked_role"]="claim"
          autonomy_record_action_outcome "$blocked_role" "$blocked_ready_task" "claim" "1"
        else
          if run_cmd "tshape_claim_ready" \
            python3 platform/automation/runtime/planner/planner_runtime_actions.py claim --board "$BOARD_FILE" \
              --role "$blocked_role" \
              --task "$blocked_ready_task" \
              --change-plan "$CHANGE_PLAN" \
              --architecture-checks "$ARCH_CHECKS"; then
            actions_taken=$((actions_taken + 1))
            AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}claim"
            AUTO_TARGET_TASK="$blocked_ready_task"
            AUTO_LAST_ACTION_BY_ROLE["$blocked_role"]="claim"
            autonomy_record_action_outcome "$blocked_role" "$blocked_ready_task" "claim" "1"
          else
            autonomy_record_action_outcome "$blocked_role" "$blocked_ready_task" "claim" "0"
          fi
        fi
      fi
    fi

    # Proof gate before complete/handoff in full_with_proofs scope.
    if (( actions_taken < DISPATCH_MAX_ACTIONS )) && [[ "$FC_ADMIN_AUTONOMY_SCOPE" == "full_with_proofs" ]]; then
      in_progress_task="$(lane_in_progress_task "$blocked_role")"
      if [[ -n "$in_progress_task" ]] && autonomy_action_allowed "$blocked_role" "$in_progress_task" "complete"; then
        role_evidence="$(contract_field "$blocked_role" "EVIDENCE")"
        role_task_update="$(extract_evidence_value "$role_evidence" "task_update")"
        role_cmd="$(extract_evidence_value "$role_evidence" "cmd")"
        role_tests="$(extract_evidence_value "$role_evidence" "tests_run")"
        role_task_id="$(extract_evidence_value "$role_evidence" "task_id")"
        role_stream_id="$(extract_evidence_value "$role_evidence" "stream_id")"
        role_artifact="$(extract_evidence_value "$role_evidence" "artifact")"
        if [[ -z "$role_artifact" ]]; then
          role_artifact="$(printf '%s\n' "$role_evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*[[:alnum:]_]*artifact[[:space:]]*=[[:space:]]*//Ip' | head -n 1 | sed 's/[[:space:]]*$//')"
        fi
        proof_gate="pass"
        missing=""
        case "$(printf '%s' "${role_task_update:-}" | tr '[:lower:]' '[:upper:]')" in
          COMPLETE|COMPLETED|DONE|HANDOFF|HANDOFF_READY) ;;
          *)
            proof_gate="deferred"
            missing="${missing}task_update;"
            ;;
        esac
        [[ -n "$role_cmd" ]] || { proof_gate="deferred"; missing="${missing}cmd;"; }
        [[ -n "$role_tests" ]] || { proof_gate="deferred"; missing="${missing}tests_run;"; }
        [[ -n "$role_artifact" ]] || { proof_gate="deferred"; missing="${missing}artifact;"; }
        if [[ "$FC_ADMIN_PROOF_GATE_STRICT" == "1" ]]; then
          if [[ -z "$role_task_id" || "$role_task_id" != "$in_progress_task" ]]; then
            proof_gate="deferred"
            missing="${missing}task_id_mismatch;"
          fi
          if [[ "$(role_has_fresh_critical_issue "$blocked_role" "$FC_ADMIN_AUTONOMY_SECURITY_WINDOW_MIN")" == "1" ]]; then
            proof_gate="deferred"
            missing="${missing}critical_recent_issue;"
          fi
        fi
        if [[ "$proof_gate" == "pass" ]]; then
          if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
            action "name=autonomy_complete dry_run=1 role=${blocked_role} task=${in_progress_task}"
            actions_taken=$((actions_taken + 1))
            AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}complete"
            AUTO_TARGET_TASK="$in_progress_task"
            AUTO_LAST_ACTION_BY_ROLE["$blocked_role"]="complete"
            AUTO_LAST_OUTCOME="resolved"
            autonomy_record_action_outcome "$blocked_role" "$in_progress_task" "complete" "1"
          else
            if run_cmd "autonomy_complete" \
              python3 platform/automation/runtime/planner/planner_runtime_actions.py complete --board "$BOARD_FILE" \
                --role "$blocked_role" \
                --task "$in_progress_task" \
                --artifact "${role_artifact:-admin_autonomy_takeover}" \
                --note "admin autonomy resolve stalled lane" \
                --exec-cmd "${role_cmd}" \
                --tests-run "${role_tests}" \
                --change-plan "$CHANGE_PLAN" \
                --architecture-checks "$ARCH_CHECKS"; then
              actions_taken=$((actions_taken + 1))
              AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}complete"
              AUTO_TARGET_TASK="$in_progress_task"
              AUTO_LAST_ACTION_BY_ROLE["$blocked_role"]="complete"
              AUTO_LAST_OUTCOME="resolved"
              autonomy_record_action_outcome "$blocked_role" "$in_progress_task" "complete" "1"
            else
              autonomy_record_action_outcome "$blocked_role" "$in_progress_task" "complete" "0"
            fi
          fi
        else
          AUTO_LAST_OUTCOME="deferred"
          AUTO_LAST_ACTION_BY_ROLE["$blocked_role"]="proof_gate_deferred"
          if [[ "$AGENT_MESSAGE_BUS_ENABLED" == "1" ]] && [[ -x "$AGENT_MESSAGE_BUS_SCRIPT" ]] && autonomy_action_allowed "$blocked_role" "${in_progress_task}" "proof_msg"; then
            miss="$(printf '%s' "${missing:-requirements_missing}" | sed 's/;$//')"
            deferred_msg="Autonomy takeover deferred for ${blocked_role}/${in_progress_task}. Missing proof gate: ${miss}. Required evidence: cmd, tests_run, artifact, task_update, task_id aligned."
            if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
              action "name=autonomy_proof_message dry_run=1 role=${blocked_role} task=${in_progress_task}"
              AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}proof_msg"
              autonomy_record_action_outcome "$blocked_role" "$in_progress_task" "proof_msg" "1"
            else
              if run_cmd "autonomy_proof_message" "$AGENT_MESSAGE_BUS_SCRIPT" post --targets "$blocked_role" --priority high --sticky 1 --ttl-min "$DISPATCH_DEP_FUNNEL_MESSAGE_TTL_MIN" --msg "$deferred_msg"; then
                AUTO_ACTION_SEQ="${AUTO_ACTION_SEQ:+${AUTO_ACTION_SEQ},}proof_msg"
                autonomy_record_action_outcome "$blocked_role" "$in_progress_task" "proof_msg" "1"
              else
                autonomy_record_action_outcome "$blocked_role" "$in_progress_task" "proof_msg" "0"
              fi
            fi
          fi
        fi
      fi
    fi
  done
fi

# 1) Handoff recovery path: ACK the oldest OPEN handoff and nudge target lane.
if (( open_handoff_count > 0 )) && (( actions_taken < DISPATCH_MAX_ACTIONS )); then
  first_handoff="$(jq -r '
    [.handoffs[]? 
      | select(((.status // "") | ascii_upcase)=="OPEN")
      | select(((.to_role // "") | test("^(planner|dev|admin)$")))
      | {id: (.id // ""), to_role: (.to_role // ""), stream_id: (.stream_id // ""), task_id: (.task_id // "")}
    ][0] // empty
  ' "$BOARD_FILE" 2>/dev/null || true)"

  hid="$(printf '%s' "$first_handoff" | jq -r '.id // ""' 2>/dev/null || true)"
  hto="$(printf '%s' "$first_handoff" | jq -r '.to_role // ""' 2>/dev/null || true)"
  hs="$(printf '%s' "$first_handoff" | jq -r '.stream_id // ""' 2>/dev/null || true)"
  ht="$(printf '%s' "$first_handoff" | jq -r '.task_id // ""' 2>/dev/null || true)"

  if [[ -n "$hid" && -n "$hto" ]]; then
    if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
      action "name=handoff_ack dry_run=1 handoff=${hid} to_role=${hto} stream=${hs:-none} task=${ht:-none}"
      actions_taken=$((actions_taken + 1))
    else
      if run_cmd "handoff_ack" python3 platform/automation/runtime/planner/planner_runtime_actions.py handoff-ack --board "$BOARD_FILE" --role "$hto" --handoff "$hid"; then
        actions_taken=$((actions_taken + 1))
      fi
    fi

    if (( actions_taken < DISPATCH_MAX_ACTIONS )) && [[ "$DISPATCH_FORCE_ROLE_TICK" == "1" ]] && [[ "$hto" != "admin" ]]; then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=nudge_role_tick dry_run=1 role=${hto}"
        actions_taken=$((actions_taken + 1))
      else
        if run_cmd "nudge_role_tick" bash scripts/fc_agent_tick.sh "$hto"; then
          actions_taken=$((actions_taken + 1))
        fi
      fi
    fi
  fi
fi

# 2) Dependency funnel plateau path (high WAITING_DEP, near-zero READY).
#    Safe actions only: sync-priority + targeted message + optional lane nudge.
if (( plateau_detected == 1 )) && (( actions_taken < DISPATCH_MAX_ACTIONS )); then
  plateau_fingerprint="qwd=${queue_waiting_dep_count}|qr=${ready_queue_count}|qip=${queue_in_progress_count}|pwd=${board_waiting_dep_count}|pip=${planner_in_progress_count}|pinprog=${planner_in_progress_tasks_csv:-none}"
  last_plateau_fingerprint="$(cat "$LAST_PLATEAU_FINGERPRINT_FILE" 2>/dev/null || true)"
  last_plateau_epoch="$(cat "$LAST_PLATEAU_ACTION_FILE" 2>/dev/null || echo 0)"
  if ! [[ "$last_plateau_epoch" =~ ^[0-9]+$ ]]; then
    last_plateau_epoch=0
  fi
  plateau_cooldown_left=0
  if (( now_epoch - last_plateau_epoch < DISPATCH_DEP_FUNNEL_COOLDOWN_SECONDS )); then
    plateau_cooldown_left=$(( DISPATCH_DEP_FUNNEL_COOLDOWN_SECONDS - (now_epoch - last_plateau_epoch) ))
  fi

  if [[ "$plateau_fingerprint" == "$last_plateau_fingerprint" ]] && (( plateau_cooldown_left > 0 )); then
    decision "skip_reason=dependency_funnel_plateau_cooldown cooldown_left_s=${plateau_cooldown_left} fingerprint=${plateau_fingerprint}"
  else
    decision "dependency_funnel_plateau_detected waiting_dep=${queue_waiting_dep_count} ready=${ready_queue_count} in_progress=${queue_in_progress_count} planner_in_progress=${planner_in_progress_count} fingerprint=${plateau_fingerprint}"
    plateau_action_taken=0

    if (( actions_taken < DISPATCH_MAX_ACTIONS )) && [[ "$DISPATCH_SYNC_PRIORITY" == "1" ]]; then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=plateau_sync_priority dry_run=1 queue=${QUEUE_FILE}"
        actions_taken=$((actions_taken + 1))
        plateau_action_taken=1
      else
        if run_cmd "plateau_sync_priority" python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board "$BOARD_FILE" --queue "$QUEUE_FILE"; then
          actions_taken=$((actions_taken + 1))
          plateau_action_taken=1
        fi
      fi
    fi

    if (( actions_taken < DISPATCH_MAX_ACTIONS )) && [[ "$AGENT_MESSAGE_BUS_ENABLED" == "1" ]] && [[ -x "$AGENT_MESSAGE_BUS_SCRIPT" ]]; then
      plateau_message="Dependency funnel detecte: WAITING_DEP=${queue_waiting_dep_count}, READY=${ready_queue_count}, IN_PROGRESS=${queue_in_progress_count}. Priorite immediate: fermer la tache planner IN_PROGRESS active puis relancer sync-priority."
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=plateau_message dry_run=1 role=${DISPATCH_DEP_FUNNEL_FORCE_ROLE}"
        actions_taken=$((actions_taken + 1))
        plateau_action_taken=1
      else
        if run_cmd "plateau_message" "$AGENT_MESSAGE_BUS_SCRIPT" post --targets "$DISPATCH_DEP_FUNNEL_FORCE_ROLE" --priority high --sticky 1 --ttl-min "$DISPATCH_DEP_FUNNEL_MESSAGE_TTL_MIN" --msg "$plateau_message"; then
          actions_taken=$((actions_taken + 1))
          plateau_action_taken=1
        fi
      fi
    fi

    if (( actions_taken < DISPATCH_MAX_ACTIONS )) && [[ "$DISPATCH_DEP_FUNNEL_FORCE_ROLE_TICK" == "1" || "$DISPATCH_FORCE_ROLE_TICK" == "1" ]]; then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=plateau_force_role_tick dry_run=1 role=${DISPATCH_DEP_FUNNEL_FORCE_ROLE}"
        actions_taken=$((actions_taken + 1))
        plateau_action_taken=1
      else
        if command -v timeout >/dev/null 2>&1; then
          if run_cmd "plateau_force_role_tick" timeout "${DISPATCH_DEP_FUNNEL_FORCE_TICK_TIMEOUT_SECONDS}" bash scripts/fc_agent_tick.sh "$DISPATCH_DEP_FUNNEL_FORCE_ROLE"; then
            actions_taken=$((actions_taken + 1))
            plateau_action_taken=1
          fi
        else
          if run_cmd "plateau_force_role_tick" bash scripts/fc_agent_tick.sh "$DISPATCH_DEP_FUNNEL_FORCE_ROLE"; then
            actions_taken=$((actions_taken + 1))
            plateau_action_taken=1
          fi
        fi
      fi
    fi

    if (( plateau_action_taken > 0 )) && [[ "$DISPATCH_DRY_RUN" != "1" ]]; then
      printf '%s\n' "$now_epoch" > "$LAST_PLATEAU_ACTION_FILE"
      printf '%s\n' "$plateau_fingerprint" > "$LAST_PLATEAU_FINGERPRINT_FILE"
    fi
  fi
fi

# 2) Queue READY + dev WIP below target => claim one DEV-01 READY task with fairness cursor.
if (( actions_taken < DISPATCH_MAX_ACTIONS )) && (( ready_queue_count > 0 )) && (( dev_in_progress_count < FC_DEV_WIP_TARGET )); then
  if [[ "$DISPATCH_SYNC_PRIORITY" == "1" ]]; then
    if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
      action "name=dev_claim_sync_priority dry_run=1 queue=${QUEUE_FILE}"
    else
      run_cmd "dev_claim_sync_priority" python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board "$BOARD_FILE" --queue "$QUEUE_FILE" || true
    fi
  fi
  fairness_pick="$(fairness_pick_ready_task "dev")"
  dev_ready_task="$(printf '%s' "$fairness_pick" | cut -f1)"
  dev_fairness_slot="$(printf '%s' "$fairness_pick" | cut -f2)"
  [[ "$dev_fairness_slot" =~ ^[0-9]+$ ]] || dev_fairness_slot=0
  if [[ -n "$dev_ready_task" ]]; then
    dev_dispatch_reason="READY_DEV_WIP_FILL"
    if (( dev_in_progress_count == 0 )); then
      dev_dispatch_reason="READY_DEV_LANE_EMPTY"
    fi
    last_dev_claim_task=""
    last_dev_claim_epoch=0
    if [[ -f "$DEV_LAST_CLAIM_FILE" ]]; then
      last_dev_claim_task="$(jq -r '.task // ""' "$DEV_LAST_CLAIM_FILE" 2>/dev/null || true)"
      last_dev_claim_epoch="$(jq -r '.epoch // 0' "$DEV_LAST_CLAIM_FILE" 2>/dev/null || echo 0)"
      [[ "$last_dev_claim_epoch" =~ ^[0-9]+$ ]] || last_dev_claim_epoch=0
    fi
    claim_cooldown_hit=0
    if [[ "$FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S" =~ ^[0-9]+$ ]] && (( FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S > 0 ))       && [[ -n "$last_dev_claim_task" && "$last_dev_claim_task" == "$dev_ready_task" ]]       && (( now_epoch - last_dev_claim_epoch < FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S )); then
      claim_cooldown_hit=1
      cooldown_remaining=$(( FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S - (now_epoch - last_dev_claim_epoch) ))
      decision "skip_reason=same_task_claim_cooldown task=${dev_ready_task} cooldown_left_s=${cooldown_remaining}"
    fi
    if (( claim_cooldown_hit == 0 )); then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=dev_claim_ready dry_run=1 task=${dev_ready_task} dispatch_reason_code=${dev_dispatch_reason} stream_fairness_slot=${dev_fairness_slot}"
        actions_taken=$((actions_taken + 1))
        DISPATCH_REASON_CODE="$dev_dispatch_reason"
        DISPATCH_FAIRNESS_SLOT="$dev_fairness_slot"
      else
        if run_cmd "dev_claim_ready"           python3 platform/automation/runtime/planner/planner_runtime_actions.py claim --board "$BOARD_FILE"             --role dev             --task "$dev_ready_task"             --change-plan "$CHANGE_PLAN"             --architecture-checks "$ARCH_CHECKS"; then
          action "name=dev_claim_ready_result role=dev task=${dev_ready_task} dispatch_reason_code=${dev_dispatch_reason} stream_fairness_slot=${dev_fairness_slot}"
          actions_taken=$((actions_taken + 1))
          DISPATCH_REASON_CODE="$dev_dispatch_reason"
          DISPATCH_FAIRNESS_SLOT="$dev_fairness_slot"
          printf '{"task":"%s","epoch":%s}
' "$dev_ready_task" "$now_epoch" > "$DEV_LAST_CLAIM_FILE"
        fi
      fi
    fi
  fi
fi

# 3) Admin READY + lane empty => claim one admin task so planner->admin dispatch becomes execution.
if [[ "$FC_ADMIN_AUTONOMY_ENABLED" == "1" ]] && (( actions_taken < DISPATCH_MAX_ACTIONS )) && (( admin_in_progress_count == 0 )); then
  admin_ready_task="$(lane_ready_task "admin")"
  if [[ -n "$admin_ready_task" ]] && autonomy_action_allowed "admin" "$admin_ready_task" "claim"; then
    if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
      action "name=admin_claim_ready dry_run=1 task=${admin_ready_task} dispatch_reason_code=ADMIN_READY_LANE_EMPTY stream_fairness_slot=1"
      actions_taken=$((actions_taken + 1))
      DISPATCH_REASON_CODE="ADMIN_READY_LANE_EMPTY"
      DISPATCH_FAIRNESS_SLOT=1
    else
      if run_cmd "admin_claim_ready" \
        python3 platform/automation/runtime/planner/planner_runtime_actions.py claim --board "$BOARD_FILE" \
          --role admin \
          --task "$admin_ready_task" \
          --change-plan "$CHANGE_PLAN" \
          --architecture-checks "$ARCH_CHECKS"; then
        action "name=admin_claim_ready_result role=admin task=${admin_ready_task} dispatch_reason_code=ADMIN_READY_LANE_EMPTY stream_fairness_slot=1"
        actions_taken=$((actions_taken + 1))
        DISPATCH_REASON_CODE="ADMIN_READY_LANE_EMPTY"
        DISPATCH_FAIRNESS_SLOT=1
      fi
    fi
  fi
fi

# 4) Queue READY + planner lane empty => sync-priority + planner claim.
if (( actions_taken < DISPATCH_MAX_ACTIONS )) && (( ready_queue_count > 0 )) && (( planner_in_progress_count == 0 )); then
  ready_ids_csv="$(jq -r '[.items[]? | select((.state // "")=="READY") | (.id // "")] | map(select(length>0)) | sort | join(",")' "$QUEUE_FILE" 2>/dev/null || true)"
  planner_ready_ids_csv="$(jq -r '[.tasks[]? | select((.role // "")=="planner" and (.state // "")=="READY") | (.id // "")] | map(select(length>0)) | sort | join(",")' "$BOARD_FILE" 2>/dev/null || true)"
  fingerprint="${ready_ids_csv}|${planner_ready_ids_csv}"
  last_fingerprint="$(cat "$LAST_FINGERPRINT_FILE" 2>/dev/null || true)"

  if [[ -n "$fingerprint" && "$fingerprint" == "$last_fingerprint" ]]; then
    decision "skip_reason=same_fingerprint ready=${ready_ids_csv:-none}"
  else
    sync_ok=1
    if [[ "$DISPATCH_SYNC_PRIORITY" == "1" ]]; then
      if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
        action "name=sync_priority dry_run=1 queue=${QUEUE_FILE}"
      else
        if ! run_cmd "sync_priority" python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --board "$BOARD_FILE" --queue "$QUEUE_FILE"; then
          sync_ok=0
        fi
      fi
    fi

    if [[ "$sync_ok" -eq 1 ]]; then
      planner_ready_task="$(jq -r '
        [.tasks[]? | select((.role // "")=="planner" and (.state // "")=="READY") | (.id // "")]
        | map(select(length>0))
        | .[0] // ""
      ' "$BOARD_FILE" 2>/dev/null || true)"

      if [[ -n "$planner_ready_task" ]]; then
        if [[ "$DISPATCH_DRY_RUN" == "1" ]]; then
          action "name=planner_claim_ready dry_run=1 task=${planner_ready_task} dispatch_reason_code=READY_PLANNER_LANE_EMPTY stream_fairness_slot=1"
          actions_taken=$((actions_taken + 1))
          DISPATCH_REASON_CODE="READY_PLANNER_LANE_EMPTY"
          DISPATCH_FAIRNESS_SLOT=1
          printf '%s\n' "$fingerprint" > "$LAST_FINGERPRINT_FILE"
        else
          if run_cmd "planner_claim_ready" \
            python3 platform/automation/runtime/planner/planner_runtime_actions.py claim --board "$BOARD_FILE" \
              --role planner \
              --task "$planner_ready_task" \
              --change-plan "$CHANGE_PLAN" \
              --architecture-checks "$ARCH_CHECKS"; then
            action "name=planner_claim_ready_result role=planner task=${planner_ready_task} dispatch_reason_code=READY_PLANNER_LANE_EMPTY stream_fairness_slot=1"
            actions_taken=$((actions_taken + 1))
            DISPATCH_REASON_CODE="READY_PLANNER_LANE_EMPTY"
            DISPATCH_FAIRNESS_SLOT=1
            printf '%s\n' "$fingerprint" > "$LAST_FINGERPRINT_FILE"
          fi
        fi
      else
        decision "no_planner_ready_after_sync ready_queue=${ready_queue_count}"
      fi
    fi
  fi
fi

if [[ "$takeover_active" == "1" && "$actions_taken" -eq 0 ]]; then
  AUTO_LAST_ACTION="takeover_noop"
  AUTO_LAST_OUTCOME="deferred"
fi
if [[ "$takeover_active" != "1" ]]; then
  AUTO_LAST_ACTION="${AUTO_LAST_ACTION:-idle}"
  AUTO_LAST_OUTCOME="${AUTO_LAST_OUTCOME:-none}"
fi
persist_autonomy_state "${blocked_roles_csv:-}" "${virtual_blocked_roles_csv:-}"

if (( actions_taken > 0 )) && [[ "$DISPATCH_REASON_CODE" == "NO_ACTION" ]]; then
  if [[ "$takeover_active" == "1" ]]; then
    DISPATCH_REASON_CODE="AUTONOMY_ACTION"
  elif (( open_handoff_count > 0 )); then
    DISPATCH_REASON_CODE="OPEN_HANDOFF_STALE"
  elif (( plateau_detected == 1 )); then
    DISPATCH_REASON_CODE="DEPENDENCY_PLATEAU"
  else
    DISPATCH_REASON_CODE="DISPATCH_ACTION"
  fi
fi

if (( actions_taken > 0 )); then
  printf '%s\n' "$now_epoch" > "$LAST_ACTION_FILE"
  result "status=OK actions=${actions_taken} takeover_active=${takeover_active} blocked_roles=${blocked_roles_csv:-none} autonomy_trigger=${AUTO_TRIGGER} autonomy_reason_code=${AUTONOMY_REASON_CODE} autonomy_target=${AUTO_TARGET_ROLE:-none} autonomy_outcome=${AUTO_LAST_OUTCOME:-partial} dispatch_reason_code=${DISPATCH_REASON_CODE} stream_fairness_slot=${DISPATCH_FAIRNESS_SLOT}"
else
  result "status=NOOP reason=no_dispatch_needed_takeover_${takeover_active} autonomy_trigger=${AUTO_TRIGGER} autonomy_reason_code=${AUTONOMY_REASON_CODE} autonomy_target=${AUTO_TARGET_ROLE:-none} autonomy_outcome=${AUTO_LAST_OUTCOME:-none} dispatch_reason_code=${DISPATCH_REASON_CODE} stream_fairness_slot=${DISPATCH_FAIRNESS_SLOT}"
fi
