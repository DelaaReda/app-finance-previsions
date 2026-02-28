#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

SESSION="${ADMINAPP_TMUX_SESSION:-adminapp_codex_sync}"
WINDOW="${ADMINAPP_TMUX_WINDOW:-adminapp-codex-main}"
HANDOFF_FILE="${ADMINAPP_HANDOFF_FILE:-docs/ops/TMUX_SESSION_HANDOFF_ADMINAPP_CODEX.md}"
CHAT_FILE="${ADMINAPP_CHAT_FILE:-docs/ops/ADMIN_TEAM_CHAT.md}"
STATE_DIR="${ADMINAPP_STATE_DIR:-/home/venom/.openclaw/cron/admin-state}"
LAST_ALERT_FILE="${STATE_DIR}/last-alert.txt"
ADMIN_AGENTS_CRON_ID="${ADMIN_AGENTS_CRON_ID:-838deae5-fa39-4052-b31d-66013faccee0}"
ADMIN_AGENTS_CRON_NAME="${ADMIN_AGENTS_CRON_NAME:-admin-agents-supervisor-15m}"
ADMIN_AGENTS_SUMMARY_OVERRIDE="${ADMINAPP_ADMIN_AGENTS_SUMMARY_OVERRIDE:-}"
AUTO_EXEC_ENABLED="${ADMINAPP_AUTO_EXEC_ENABLED:-1}"
ACTION_COOLDOWN_SECONDS="${ADMINAPP_ACTION_COOLDOWN_SECONDS:-900}"
ACTION_STALL_KEY_FILE="${STATE_DIR}/admin-action-stall-key.txt"
ACTION_STALL_COUNT_FILE="${STATE_DIR}/admin-action-stall-count.txt"
ACTION_LAST_EXEC_SIG_FILE="${STATE_DIR}/admin-action-last-exec-signature.txt"
ACTION_LAST_EXEC_TS_FILE="${STATE_DIR}/admin-action-last-exec-ts.txt"
ACTION_LAST_ROUTED_ID_FILE="${STATE_DIR}/admin-action-last-routed-id.txt"
ROLE_TRACE_DIR="${ADMINAPP_ROLE_TRACE_DIR:-logs-codex-runs/role-runner}"
PRIORITY_QUEUE_FILE="${ADMINAPP_PRIORITY_QUEUE_FILE:-docs/orchestrator-ops/priority-queue.json}"
EXEC_LATEST_FILE="${ADMINAPP_EXEC_LATEST_FILE:-docs/orchestrator-ops/executors-monitoring-latest.json}"
ROLE_TOPOLOGY_FILE="${ADMINAPP_ROLE_TOPOLOGY_FILE:-docs/orchestrator-ops/parallel-role-topology.json}"
OPENCLAW_BIN="${ADMINAPP_OPENCLAW_BIN:-}"
RUNNING_STALE_SECONDS="${ADMINAPP_RUNNING_STALE_SECONDS:-330}"
STALE_SWEEP_SCRIPT="${ADMINAPP_STALE_SWEEP_SCRIPT:-scripts/stale_cron_sweep.sh}"
CIRCUIT_BREAKER_SCRIPT="${ADMINAPP_CIRCUIT_BREAKER_SCRIPT:-scripts/orchestration_circuit_breaker.sh}"
CIRCUIT_BREAKER_ERROR_THRESHOLD="${ADMINAPP_CIRCUIT_BREAKER_ERROR_THRESHOLD:-3}"

ROLE_MEMORY_DIR="${ADMINAPP_ROLE_MEMORY_DIR:-$ROOT/memory/agents}"
ADMIN_MEMORY_FILE="${ROLE_MEMORY_DIR}/adminapp-codex.md"
ADMIN_MEMORY_LOCK_FILE="${STATE_DIR}/adminapp-codex.memory.lock"
ROLE_PROBE_AGENT_BIN="${ADMINAPP_ROLE_PROBE_AGENT_BIN:-codex}"
ROLE_PROBE_RETRY_ENGINE="${ADMINAPP_ROLE_PROBE_RETRY_ENGINE:-sdk}"
ROLE_PROBE_CODEX_FALLBACK="${ADMINAPP_ROLE_PROBE_CODEX_FALLBACK:-0}"

if [[ "${ROLE_PROBE_AGENT_BIN,,}" != "codex" && "$ROLE_PROBE_RETRY_ENGINE" == "sdk" ]]; then
  ROLE_PROBE_RETRY_ENGINE="tmux"
fi

mkdir -p "$STATE_DIR"
mkdir -p "$ROLE_MEMORY_DIR"

if ! [[ "$CIRCUIT_BREAKER_ERROR_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$CIRCUIT_BREAKER_ERROR_THRESHOLD" -lt 1 ]]; then
  CIRCUIT_BREAKER_ERROR_THRESHOLD=3
fi

read_file_or_empty() {
  local path="$1"
  if [[ -f "$path" ]]; then
    cat "$path" 2>/dev/null || true
  fi
}

file_mtime() {
  local path="$1"
  if [[ -f "$path" ]]; then
    stat -c %Y "$path" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

update_action_stall_counter() {
  local key="$1"
  local prev_key=""
  local prev_count=0
  local new_count=1
  prev_key="$(read_file_or_empty "$ACTION_STALL_KEY_FILE")"
  if [[ -f "$ACTION_STALL_COUNT_FILE" ]]; then
    prev_count="$(cat "$ACTION_STALL_COUNT_FILE" 2>/dev/null || echo 0)"
  fi
  if [[ ! "$prev_count" =~ ^[0-9]+$ ]]; then
    prev_count=0
  fi
  if [[ -n "$key" && "$key" == "$prev_key" ]]; then
    new_count=$((prev_count + 1))
  fi
  printf '%s\n' "$key" > "$ACTION_STALL_KEY_FILE"
  printf '%s\n' "$new_count" > "$ACTION_STALL_COUNT_FILE"
  printf '%s\n' "$new_count"
}

reset_action_stall_counter() {
  : > "$ACTION_STALL_KEY_FILE"
  printf '0\n' > "$ACTION_STALL_COUNT_FILE"
}

action_cooldown_active() {
  local signature="$1"
  local now_epoch=0
  local last_sig=""
  local last_ts=0
  now_epoch="$(date -u +%s)"
  last_sig="$(read_file_or_empty "$ACTION_LAST_EXEC_SIG_FILE")"
  if [[ -f "$ACTION_LAST_EXEC_TS_FILE" ]]; then
    last_ts="$(cat "$ACTION_LAST_EXEC_TS_FILE" 2>/dev/null || echo 0)"
  fi
  if [[ ! "$last_ts" =~ ^[0-9]+$ ]]; then
    last_ts=0
  fi
  if [[ "$signature" == "$last_sig" && "$last_ts" -gt 0 ]]; then
    if [[ $((now_epoch - last_ts)) -lt "$ACTION_COOLDOWN_SECONDS" ]]; then
      return 0
    fi
  fi
  return 1
}

mark_action_executed_now() {
  local signature="$1"
  local now_epoch=0
  now_epoch="$(date -u +%s)"
  printf '%s\n' "$signature" > "$ACTION_LAST_EXEC_SIG_FILE"
  printf '%s\n' "$now_epoch" > "$ACTION_LAST_EXEC_TS_FILE"
}

trim_value() {
  printf '%s' "${1:-}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//'
}

normalize_role_name() {
  local value=""
  value="$(trim_value "${1:-}")"
  value="${value//-/_}"
  printf '%s\n' "$value"
}

role_session_default() {
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    analyst) echo "codex_analyst_cron" ;;
    architect) echo "codex_architect_cron" ;;
    backend_engineer) echo "codex_backend_engineer_cron" ;;
    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
    data_analyst) echo "codex_data_analyst_cron" ;;
    infra_engineer) echo "codex_infra_engineer_cron" ;;
    integrator) echo "codex_integrator_cron" ;;
    dev) echo "codex_dev_cron" ;;
    tester) echo "codex_tester_cron" ;;
    qa) echo "codex_qa_cron" ;;
    po) echo "codex_po_cron" ;;
    scrum_master) echo "codex_scrum_master_cron" ;;
    clawsentinel) echo "clawsentinel" ;;
    *) echo "" ;;
  esac
}

role_trace_default() {
  case "$1" in
    scrum_master) echo "scrum_master.live.log" ;;
    *) echo "$1.live.log" ;;
  esac
}

role_trace_path() {
  local role=""
  local trace=""
  role="$(normalize_role_name "${1:-}")"
  if [[ -f "$ROLE_TOPOLOGY_FILE" ]]; then
    trace="$(jq -r --arg r "$role" '.roles[]? | select(.role==$r) | .trace_file // empty' "$ROLE_TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$trace" ]]; then
    printf '%s\n' "$trace"
    return 0
  fi
  printf '%s/%s\n' "$ROLE_TRACE_DIR" "$(role_trace_default "$role")"
}

role_session_name() {
  local role=""
  local session=""
  role="$(normalize_role_name "${1:-}")"
  if [[ -f "$ROLE_TOPOLOGY_FILE" ]]; then
    session="$(jq -r --arg r "$role" '.roles[]? | select(.role==$r) | .session_name // empty' "$ROLE_TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$session" ]]; then
    printf '%s\n' "$session"
    return 0
  fi
  role_session_default "$role"
}

role_from_job_name() {
  local name=""
  name="$(trim_value "${1:-}")"
  name="${name%-tmux-loop}"
  printf '%s\n' "${name//-/_}"
}

role_exists_in_topology() {
  local role=""
  role="$(normalize_role_name "${1:-}")"
  if [[ -f "$ROLE_TOPOLOGY_FILE" ]]; then
    jq -e --arg r "$role" '.roles[]? | select(.role==$r)' "$ROLE_TOPOLOGY_FILE" >/dev/null 2>&1
    return $?
  fi
  case "$role" in
    planner|analyst|architect|backend_engineer|frontend_engineer|data_analyst|infra_engineer|integrator|dev|tester|qa|po|scrum_master|clawsentinel) return 0 ;;
    *) return 1 ;;
  esac
}

ensure_role_session_exists() {
  local role=""
  local session=""
  role="$(normalize_role_name "${1:-}")"
  session="$(role_session_name "$role")"
  if [[ -z "$session" ]]; then
    return 1
  fi
  if tmux has-session -t "$session" 2>/dev/null; then
    return 0
  fi
  tmux new-session -d -s "$session" -c "$ROOT"
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  tmux send-keys -t "$session:0.0" "cd $ROOT" C-m
  return 0
}

run_probe_for_role() {
  local role=""
  local trace=""
  role="$(normalize_role_name "${1:-}")"
  if ! role_exists_in_topology "$role"; then
    return 1
  fi
  trace="$(role_trace_path "$role")"
  run_role_probe_once "$role" "$trace"
}

force_run_failed_roles_then_recheck() {
  local cron_json=""
  local failed_jobs=()
  local role=""
  local ok_count=0
  local fail_count=0
  local attempted=()

  cron_json="$("$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  mapfile -t failed_jobs < <(printf '%s' "$cron_json" | jq -r '.jobs[] | select((.name | test("-tmux-loop$")) and (.state.lastStatus=="error")) | .name' 2>/dev/null || true)
  if [[ "${#failed_jobs[@]}" -eq 0 ]]; then
    ACTION_EXEC_DETAILS="failed_jobs=0;probed_ok=0;probed_failed=0"
    return 0
  fi

  for job_name in "${failed_jobs[@]}"; do
    role="$(role_from_job_name "$job_name")"
    attempted+=("$role")
    if run_probe_for_role "$role"; then
      ok_count=$((ok_count + 1))
    else
      fail_count=$((fail_count + 1))
    fi
  done

  ACTION_EXEC_DETAILS="failed_jobs=${#failed_jobs[@]};probed_ok=${ok_count};probed_failed=${fail_count};roles=$(IFS=,; echo "${attempted[*]}")"
  if [[ "$fail_count" -gt 0 ]]; then
    return 1
  fi
  return 0
}

force_run_blocked_roles_then_recheck() {
  local blocked_roles=()
  local role=""
  local ok_count=0
  local fail_count=0
  local attempted=()

  if [[ ! -f "$EXEC_LATEST_FILE" ]]; then
    ACTION_EXEC_DETAILS="blocked_roles=0;reason=exec_latest_missing"
    return 0
  fi

  mapfile -t blocked_roles < <(jq -r '(.summary.blocker_roles // [])[]? | select(type=="string" and length>0)' "$EXEC_LATEST_FILE" 2>/dev/null || true)
  if [[ "${#blocked_roles[@]}" -eq 0 ]]; then
    ACTION_EXEC_DETAILS="blocked_roles=0;probed_ok=0;probed_failed=0"
    return 0
  fi

  for role in "${blocked_roles[@]}"; do
    role="$(normalize_role_name "$role")"
    [[ -z "$role" ]] && continue
    attempted+=("$role")
    if run_probe_for_role "$role"; then
      ok_count=$((ok_count + 1))
    else
      fail_count=$((fail_count + 1))
    fi
  done

  ACTION_EXEC_DETAILS="blocked_roles=${#blocked_roles[@]};probed_ok=${ok_count};probed_failed=${fail_count};roles=$(IFS=,; echo "${attempted[*]}")"
  if [[ "$fail_count" -gt 0 ]]; then
    return 1
  fi
  return 0
}

verify_scheduler_lane_and_recent_runs() {
  local cron_json=""
  local role_total=0
  local role_enabled=0
  local role_error=0
  local role_running=0
  local stale=0

  cron_json="$("$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  role_total="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.name | test("-tmux-loop$"))] | length' 2>/dev/null || echo 0)"
  role_enabled="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.name | test("-tmux-loop$")) and .enabled==true)] | length' 2>/dev/null || echo 0)"
  role_error="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.name | test("-tmux-loop$")) and .state.lastStatus=="error")] | length' 2>/dev/null || echo 0)"
  role_running="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.name | test("-tmux-loop$")) and .state.runningAtMs!=null)] | length' 2>/dev/null || echo 0)"
  if run_stale_sweep_preview; then
    stale="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "stale")"
  fi
  if [[ ! "$stale" =~ ^[0-9]+$ ]]; then
    stale=0
  fi
  ACTION_EXEC_DETAILS="role_total=${role_total};role_enabled=${role_enabled};role_running=${role_running};role_error=${role_error};stale_running=${stale}"
  return 0
}

rebuild_role_cron_jobs_from_configure_script() {
  local out=""
  local rc=0
  set +e
  out="$(bash scripts/configure_parallel_team_crons.sh --apply --enable 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    ACTION_EXEC_DETAILS="reprovision_failed;rc=${rc}"
    return 1
  fi
  if run_probe_for_role "planner"; then
    ACTION_EXEC_DETAILS="reprovision_ok;planner_probe=ok"
    return 0
  fi
  ACTION_EXEC_DETAILS="reprovision_ok;planner_probe=failed"
  return 1
}

enable_roles_sequential_for_delivery_validation() {
  local cron_json=""
  local ids=()
  local enabled_count=0
  local id=""
  cron_json="$("$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  mapfile -t ids < <(printf '%s' "$cron_json" | jq -r '.jobs[] | select((.name | test("-tmux-loop$")) and .enabled==false) | .id' 2>/dev/null || true)
  for id in "${ids[@]}"; do
    if [[ -n "$id" ]]; then
      if "$OPENCLAW_BIN" cron enable "$id" >/dev/null 2>&1; then
        enabled_count=$((enabled_count + 1))
      fi
    fi
  done
  if run_probe_for_role "planner"; then
    ACTION_EXEC_DETAILS="enabled_roles=${enabled_count};planner_probe=ok"
    return 0
  fi
  ACTION_EXEC_DETAILS="enabled_roles=${enabled_count};planner_probe=failed"
  return 1
}

ACTION_CANON_NAME=""
ACTION_CANON_ARG1=""
ACTION_CANON_ARGS=""

parse_action_expression() {
  local raw=""
  local parsed_payload=""
  local parsed_name=""
  local parsed_args=""

  ACTION_CANON_NAME=""
  ACTION_CANON_ARGS=""
  ACTION_CANON_ARG1=""

  raw="$(trim_value "${1:-}")"
  if [[ -z "$raw" ]]; then
    return 0
  fi

  parsed_payload="$(python3 - "$raw" <<'PY'
import re
import sys

raw = (sys.argv[1] or "").strip().replace("\r", " ").replace("\n", " ")
if not raw:
    print("")
    sys.exit(0)

raw = re.sub(r"^(?:action|next_action)\s*(?:[:=]|=>)\s*", "", raw, flags=re.IGNORECASE)
raw = re.sub(r"^(?:action|next_action)\s+", "", raw, flags=re.IGNORECASE)
raw = raw.strip().strip('";\\'')
raw = raw.strip().strip(";,")
if not raw:
    print("")
    sys.exit(0)

m = re.match(r"^([A-Za-z0-9_.-]+)\s*(?:\(\s*([^)]*?)\s*\))?\s*(.*)$", raw)
if not m:
    print("")
    sys.exit(0)

name = (m.group(1) or "").lower().strip()
args = (m.group(2) or "").strip()
suffix = (m.group(3) or "").strip()

name = re.sub(r"\s+", "_", name)
name = re.sub(r"[^a-z0-9_]+", "_", name)
name = re.sub(r"_+", "_", name).strip("_")

suffix = suffix.lower().strip()
suffix = re.sub(r"^[\s_\-:.]+", "", suffix)
suffix = re.sub(r"[^a-z0-9_]+", "_", suffix).strip("_")

if suffix:
    if suffix == "and_verify_new_role_output":
        name = f"{name}_{suffix}"
    else:
        name = f"{name}_{suffix}"

args = re.sub(r"\s+", "_", args)
print(f"{name}|{args}")
PY
  )"

  if [[ -n "$parsed_payload" && "$parsed_payload" == *"|"* ]]; then
    parsed_name="${parsed_payload%%|*}"
    parsed_args="${parsed_payload#*|}"
  else
    parsed_name=""
    parsed_args=""
  fi

  ACTION_CANON_NAME="$(printf '%s' "${parsed_name:-$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_' | tr -s '_' | sed 's/^_\\|_$//g') }")"
  ACTION_CANON_ARGS="$(trim_value "$parsed_args")"
  case "$ACTION_CANON_NAME" in
    force_run_issue_roles_then_recheck) ACTION_CANON_NAME="force_run_failed_roles_then_recheck" ;;
    force_run_issue_role_then_recheck) ACTION_CANON_NAME="force_run_failed_roles_then_recheck" ;;
    force_run_issue_roles_and_verify_new_role_output) ACTION_CANON_NAME="force_run_failed_roles_then_recheck" ;;
    if_delivery_needed_enable_sequential_mode_starting_planner) ACTION_CANON_NAME="if_delivery_needed_enable_sequential_mode_starting_planner" ;;
    reactivate_one_role_sequential_and_verify_new_role_output) ACTION_CANON_NAME="reactivate_one_role_sequential_and_verify_new_role_output" ;;
    recreate_missing_sessions_then_validate_one_role) ACTION_CANON_NAME="recreate_missing_sessions_then_validate_one_role" ;;
    recreate-missing-sessions-then-validate-one-role) ACTION_CANON_NAME="recreate_missing_sessions_then_validate_one_role" ;;
  esac

  if [[ -n "$ACTION_CANON_ARGS" ]]; then
    ACTION_CANON_ARG1="$(trim_value "${ACTION_CANON_ARGS%%,*}")"
    ACTION_CANON_ARG1="$(normalize_role_name "$ACTION_CANON_ARG1")"
  fi
}

route_handoff_to_chat() {
  local owner="$1"
  local issue="$2"
  local action="$3"
  local action_id="$4"
  local action_scope="$5"
  local ts_local=""
  local last_routed=""
  if [[ -z "$action_id" || "$action_id" == "none" ]]; then
    return 0
  fi
  last_routed="$(read_file_or_empty "$ACTION_LAST_ROUTED_ID_FILE")"
  if [[ "$last_routed" == "$action_id" ]]; then
    return 0
  fi
  if [[ ! -f "$CHAT_FILE" ]]; then
    return 0
  fi
  ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
  printf -- "- [%s] [adminapp-codex] TYPE: HANDOFF MSG: action %s routee vers %s (scope=%s, issue=%s). NEXT: %s.\n" \
    "$ts_local" "$action_id" "${owner:-unknown}" "${action_scope:-none}" "${issue:-none}" "${action:-none}" >> "$CHAT_FILE"
  printf '%s\n' "$action_id" > "$ACTION_LAST_ROUTED_ID_FILE"
}

run_role_probe_once() {
  local role="$1"
  local trace="$2"
  local pre_mtime=0
  local post_mtime=0
  local out=""
  local probe_state_dir=""
  probe_state_dir="/tmp/openclaw-role-probe-state/${role}"
  mkdir -p "$probe_state_dir"
  pre_mtime="$(file_mtime "$trace")"
  out="$(TMUX_ROLE_AGENT_BIN="$ROLE_PROBE_AGENT_BIN" TMUX_ROLE_RETRY_ENGINE_DEFAULT="$ROLE_PROBE_RETRY_ENGINE" PROMPT_TIMEOUT_SECONDS=25 RETRY_PROMPT_TIMEOUT_SECONDS=10 TMUX_ROLE_STALL_ABORT_SECONDS=10 SKIP_RETRY_ON_TIMEOUT=1 TMUX_ROLE_CODEX_EXEC_FALLBACK="$ROLE_PROBE_CODEX_FALLBACK" TMUX_ROLE_CODEX_EXEC_RESUME=1 TMUX_ROLE_ALLOW_FILE_EDITS=0 TMUX_ROLE_STATE_DIR="$probe_state_dir" TMUX_ROLE_PUBLISH_MONITORING=0 bash scripts/cron_tmux_role_runner.sh "$role" 2>&1 || true)"
  post_mtime="$(file_mtime "$trace")"
  if [[ "$post_mtime" -gt "$pre_mtime" ]]; then
    return 0
  fi
  if printf '%s\n' "$out" | rg -q "ROLE=${role} .*VERDICT="; then
    return 0
  fi
  return 1
}

parse_sweep_field() {
  local summary="$1"
  local key="$2"
  printf '%s\n' "$summary" | sed -n "s/.*${key}=\\([0-9][0-9]*\\).*/\\1/p" | head -n 1
}

STALE_SWEEP_LAST_SUMMARY=""

run_stale_sweep_preview() {
  local out=""
  local summary=""
  local rc=0
  STALE_SWEEP_LAST_SUMMARY=""
  if [[ ! -x "$STALE_SWEEP_SCRIPT" ]]; then
    return 1
  fi
  set +e
  out="$(
    STALE_SWEEP_OPENCLAW_BIN="$OPENCLAW_BIN" \
    bash "$STALE_SWEEP_SCRIPT" --dry-run --threshold "$RUNNING_STALE_SECONDS" 2>/dev/null
  )"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    return 1
  fi
  summary="$(printf '%s\n' "$out" | rg '^SWEEP_SUMMARY ' | tail -n 1 || true)"
  if [[ -z "$summary" ]]; then
    return 1
  fi
  STALE_SWEEP_LAST_SUMMARY="$summary"
  return 0
}

run_stale_sweep_action() {
  local out=""
  local summary=""
  local rc=0
  local stale=0
  local reset_ok=0
  local reset_failed=0
  local skipped_live=0

  if [[ ! -x "$STALE_SWEEP_SCRIPT" ]]; then
    ACTION_EXEC_RESULT="failed"
    ACTION_EXEC_DETAILS="stale_sweep_script_missing"
    return 1
  fi

  set +e
  out="$(
    STALE_SWEEP_OPENCLAW_BIN="$OPENCLAW_BIN" \
    bash "$STALE_SWEEP_SCRIPT" --apply --threshold "$RUNNING_STALE_SECONDS" 2>&1
  )"
  rc=$?
  set -e

  summary="$(printf '%s\n' "$out" | rg '^SWEEP_SUMMARY ' | tail -n 1 || true)"
  if [[ -z "$summary" ]]; then
    ACTION_EXEC_RESULT="failed"
    ACTION_EXEC_DETAILS="stale_sweep_no_summary"
    return 1
  fi
  STALE_SWEEP_LAST_SUMMARY="$summary"

  stale="$(parse_sweep_field "$summary" "stale")"
  reset_ok="$(parse_sweep_field "$summary" "reset_ok")"
  reset_failed="$(parse_sweep_field "$summary" "reset_failed")"
  skipped_live="$(parse_sweep_field "$summary" "skipped_live")"

  if [[ ! "$stale" =~ ^[0-9]+$ ]]; then stale=0; fi
  if [[ ! "$reset_ok" =~ ^[0-9]+$ ]]; then reset_ok=0; fi
  if [[ ! "$reset_failed" =~ ^[0-9]+$ ]]; then reset_failed=0; fi
  if [[ ! "$skipped_live" =~ ^[0-9]+$ ]]; then skipped_live=0; fi

  ACTION_EXEC_DETAILS="stale_jobs=${stale};reset_ok=${reset_ok};reset_failed=${reset_failed};skip_live=${skipped_live}"
  if [[ $rc -eq 0 && "$reset_failed" -eq 0 ]]; then
    ACTION_EXEC_RESULT="done"
    return 0
  fi
  ACTION_EXEC_RESULT="failed"
  return 1
}

resolve_openclaw_bin() {
  local candidate=""
  if [[ -n "$OPENCLAW_BIN" && -x "$OPENCLAW_BIN" ]]; then
    printf '%s\n' "$OPENCLAW_BIN"
    return 0
  fi
  for candidate in \
    "/home/venom/.npm-global/bin/openclaw" \
    "${HOME}/.npm-global/bin/openclaw" \
    "$(command -v openclaw 2>/dev/null || true)" \
    "/usr/local/bin/openclaw" \
    "/usr/bin/openclaw" \
    "/bin/openclaw"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

normalize_cron_runs_json() {
  local raw="${1:-}"
  if command -v python3 >/dev/null 2>&1 && [[ -f "${ROOT}/scripts/openclaw_cron_runs_normalize.py" ]]; then
    printf '%s' "$raw" | python3 "${ROOT}/scripts/openclaw_cron_runs_normalize.py" 2>/dev/null || echo '{"entries":[]}'
  else
    printf '%s' "$raw"
  fi
}

latest_cron_run_summary() {
  local job_id="$1"
  local limit="${2:-1}"
  local runs_raw=""
  local runs_json=""
  if [[ -z "$job_id" ]]; then
    printf ''
    return 0
  fi
  runs_raw="$("$OPENCLAW_BIN" cron runs --id "$job_id" --limit "$limit" 2>/dev/null || echo '{}')"
  runs_json="$(normalize_cron_runs_json "$runs_raw")"
  printf '%s' "$runs_json" | jq -r '.entries[0].summary // .entries[0].error // ""' 2>/dev/null || true
}

resolve_cron_id_by_name() {
  local cron_name="$1"
  local cron_json="${2:-}"
  local resolved_id=""
  if [[ -z "$cron_name" ]]; then
    printf ''
    return 0
  fi
  if [[ -z "$cron_json" ]]; then
    cron_json="$("$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  fi
  resolved_id="$(printf '%s' "$cron_json" | jq -r --arg n "$cron_name" '.jobs[]? | select(.name==$n) | .id' | head -n 1)"
  if [[ "$resolved_id" == "null" ]]; then
    resolved_id=""
  fi
  printf '%s' "$resolved_id"
}

execute_admin_action() {
  local action="$1"
  local action_name=""
  local action_arg1=""
  local extra_details=""
  local target_role=""
  local _roles_for_sessions=()
  ACTION_EXEC_RESULT="none"
  ACTION_EXEC_DETAILS="none"
  parse_action_expression "$action"
  action_name="$ACTION_CANON_NAME"
  action_arg1="$(normalize_role_name "${ACTION_CANON_ARG1:-}")"
  case "$action_name" in
    force_run_issue_roles_then_recheck)
      action_name="force_run_failed_roles_then_recheck"
      ;;
  esac
  case "$action_name" in
    reset_stale_running_role_jobs_then_force_run_planner_backend_frontend)
      if run_stale_sweep_action && run_probe_for_role "planner" && run_probe_for_role "backend_engineer" && run_probe_for_role "frontend_engineer"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner+backend+frontend_refresh_ok"
      else
        if [[ "$ACTION_EXEC_RESULT" == "none" || "$ACTION_EXEC_RESULT" == "done" ]]; then
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner_or_backend_or_frontend_refresh_failed"
        fi
      fi
      ;;
    reset_stale_running_role_jobs_then_force_run_planner_backend)
      if run_stale_sweep_action && run_probe_for_role "planner" && run_probe_for_role "backend_engineer"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner+backend_refresh_ok"
      else
        if [[ "$ACTION_EXEC_RESULT" == "none" || "$ACTION_EXEC_RESULT" == "done" ]]; then
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner_or_backend_refresh_failed"
        fi
      fi
      ;;
    reset_stale_running_role_jobs_then_force_run_planner_dev)
      if run_stale_sweep_action && run_probe_for_role "planner" && run_probe_for_role "dev"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner+dev_refresh_ok"
      else
        if [[ "$ACTION_EXEC_RESULT" == "none" || "$ACTION_EXEC_RESULT" == "done" ]]; then
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner_or_dev_refresh_failed"
        fi
      fi
      ;;
    force_run_planner_then_dev_and_confirm_live_logs_refresh)
      if run_probe_for_role "planner" && run_probe_for_role "dev"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="planner+dev_refresh_ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="planner_or_dev_refresh_failed"
      fi
      ;;
    force_run_planner_then_backend_and_confirm_live_logs_refresh)
      if run_probe_for_role "planner" && run_probe_for_role "backend_engineer"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="planner+backend_refresh_ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="planner_or_backend_refresh_failed"
      fi
      ;;
    force_run_planner_then_backend_and_frontend_then_confirm_live_logs_refresh)
      if run_probe_for_role "planner" && run_probe_for_role "backend_engineer" && run_probe_for_role "frontend_engineer"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="planner+backend+frontend_refresh_ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="planner_or_backend_or_frontend_refresh_failed"
      fi
      ;;
    recreate_missing_sessions_then_validate_one_role)
      target_role="${action_arg1:-planner}"
      if ! role_exists_in_topology "$target_role"; then
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="invalid_role=${target_role}"
      else
        mapfile -t _roles_for_sessions < <(jq -r '.roles[]?.role' "$ROLE_TOPOLOGY_FILE" 2>/dev/null || true)
        if [[ "${#_roles_for_sessions[@]}" -eq 0 ]]; then
          _roles_for_sessions=(planner analyst architect backend_engineer frontend_engineer data_analyst infra_engineer integrator dev tester qa po scrum_master clawsentinel)
        fi
        local missing_before=0
        local created_count=0
        local role_name=""
        for role_name in "${_roles_for_sessions[@]}"; do
          role_name="$(normalize_role_name "$role_name")"
          if [[ -z "$role_name" ]]; then
            continue
          fi
          local session_name=""
          session_name="$(role_session_name "$role_name")"
          if [[ -z "$session_name" ]]; then
            continue
          fi
          if ! tmux has-session -t "$session_name" 2>/dev/null; then
            missing_before=$((missing_before + 1))
            if ensure_role_session_exists "$role_name"; then
              created_count=$((created_count + 1))
            else
              ACTION_EXEC_RESULT="failed"
              ACTION_EXEC_DETAILS="missing_before=${missing_before};created=${created_count};create_failed_role=${role_name}"
              return 0
            fi
          fi
        done
        if run_probe_for_role "$target_role"; then
          ACTION_EXEC_RESULT="done"
          ACTION_EXEC_DETAILS="missing_before=${missing_before};created=${created_count};validated_role=${target_role}"
        else
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="missing_before=${missing_before};created=${created_count};validated_role=${target_role};validate_failed=1"
        fi
      fi
      ;;
    reactivate_one_role_sequential_and_verify_new_role_output)
      target_role="${action_arg1:-planner}"
      if run_probe_for_role "$target_role"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="reactivated_role=${target_role};probe=ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="reactivated_role=${target_role};probe=failed"
      fi
      ;;
    force_run_failed_roles_then_recheck)
      if force_run_failed_roles_then_recheck; then
        ACTION_EXEC_RESULT="done"
      else
        ACTION_EXEC_RESULT="failed"
      fi
      ;;
    force_run_blocked_roles_then_recheck)
      if force_run_blocked_roles_then_recheck; then
        ACTION_EXEC_RESULT="done"
      else
        ACTION_EXEC_RESULT="failed"
      fi
      ;;
    verify_scheduler_lane_and_recent_runs)
      if verify_scheduler_lane_and_recent_runs; then
        ACTION_EXEC_RESULT="done"
      else
        ACTION_EXEC_RESULT="failed"
      fi
      ;;
    rebuild_role_cron_jobs_from_configure_script)
      if rebuild_role_cron_jobs_from_configure_script; then
        ACTION_EXEC_RESULT="done"
      else
        ACTION_EXEC_RESULT="failed"
      fi
      ;;
    enable_roles_sequential_for_delivery_validation|if_delivery_needed_enable_sequential_mode_starting_planner)
      if enable_roles_sequential_for_delivery_validation; then
        ACTION_EXEC_RESULT="done"
      else
        ACTION_EXEC_RESULT="failed"
      fi
      ;;
    keep_monitoring|keep_monitoring_no_ready_items)
      ACTION_EXEC_RESULT="done"
      ACTION_EXEC_DETAILS="no_execution_required"
      ;;
    *)
      ACTION_EXEC_RESULT="unsupported"
      ACTION_EXEC_DETAILS="unsupported_action"
      ;;
  esac
  extra_details="parsed_action=${action_name}"
  if [[ -n "$action_arg1" ]]; then
    extra_details="${extra_details};parsed_arg1=${action_arg1}"
  fi
  if [[ "$ACTION_EXEC_DETAILS" == "none" || -z "$ACTION_EXEC_DETAILS" ]]; then
    ACTION_EXEC_DETAILS="$extra_details"
  else
    ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};${extra_details}"
  fi
}

if ! command -v tmux >/dev/null 2>&1; then
  echo "STATUS: BLOCKED"
  echo "DELTA: tmux_absent"
  echo "EVIDENCE: command=tmux missing_from_PATH"
  echo "RISKS: impossible de maintenir la session admin en continu"
  echo "NEXT: installer tmux ou corriger PATH"
  echo "VERDICT: BLOCKED"
  echo "BLOCKER_ID: TMUX_MISSING"
  echo "NEXT_ACTION_UNIQUE: ADMINAPP_FIX_TMUX_$(date +%Y%m%d%H%M%S)"
  exit 0
fi

if ! OPENCLAW_BIN="$(resolve_openclaw_bin)"; then
  echo "STATUS: BLOCKED"
  echo "DELTA: openclaw_absent"
  echo "EVIDENCE: command=openclaw missing_from_PATH"
  echo "RISKS: monitoring cron indisponible"
  echo "NEXT: installer openclaw CLI ou corriger PATH"
  echo "VERDICT: BLOCKED"
  echo "BLOCKER_ID: OPENCLAW_MISSING"
  echo "NEXT_ACTION_UNIQUE: ADMINAPP_FIX_OPENCLAW_$(date +%Y%m%d%H%M%S)"
  exit 0
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -c "$ROOT"
fi

if ! tmux list-windows -t "$SESSION" -F '#W' | rg -qx "$WINDOW"; then
  tmux rename-window -t "${SESSION}:0" "$WINDOW" >/dev/null 2>&1 || true
fi

tmux set-environment -t "$SESSION" ADMIN_ROLE adminapp-codex
tmux set-option -t "$SESSION" history-limit 200000 >/dev/null 2>&1 || true

if [[ -f "$HANDOFF_FILE" ]]; then
  tmux set-environment -t "$SESSION" ADMIN_HANDOFF_FILE "$HANDOFF_FILE"
fi

cron_json="$("$OPENCLAW_BIN" cron list --json)"
total_jobs="$(printf '%s' "$cron_json" | jq '.jobs | length')"
ok_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="ok")] | length')"
running_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.runningAtMs!=null)] | length')"
error_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="error")] | length')"
timeout_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.state.lastError // "") | test("timed out"; "i"))] | length')"
pending_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus==null)] | length')"
stale_running_jobs=0
stale_running_skipped_live=0
if run_stale_sweep_preview; then
  stale_running_jobs="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "stale")"
  stale_running_skipped_live="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "skipped_live")"
fi
if [[ ! "$stale_running_jobs" =~ ^[0-9]+$ ]]; then
  stale_running_jobs=0
fi
if [[ ! "$stale_running_skipped_live" =~ ^[0-9]+$ ]]; then
  stale_running_skipped_live=0
fi

stale_auto_exec_result="none"
stale_auto_exec_details="none"
if [[ "$AUTO_EXEC_ENABLED" == "1" && "$stale_running_jobs" -gt 0 ]]; then
  if run_stale_sweep_action; then
    stale_auto_exec_result="done"
  else
    stale_auto_exec_result="failed"
  fi
  stale_auto_exec_details="$ACTION_EXEC_DETAILS"

  cron_json="$("$OPENCLAW_BIN" cron list --json)"
  total_jobs="$(printf '%s' "$cron_json" | jq '.jobs | length')"
  ok_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="ok")] | length')"
  running_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.runningAtMs!=null)] | length')"
  error_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="error")] | length')"
  timeout_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.state.lastError // "") | test("timed out"; "i"))] | length')"
  pending_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus==null)] | length')"

  stale_running_jobs=0
  stale_running_skipped_live=0
  if run_stale_sweep_preview; then
    stale_running_jobs="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "stale")"
    stale_running_skipped_live="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "skipped_live")"
  fi
  if [[ ! "$stale_running_jobs" =~ ^[0-9]+$ ]]; then
    stale_running_jobs=0
  fi
  if [[ ! "$stale_running_skipped_live" =~ ^[0-9]+$ ]]; then
    stale_running_skipped_live=0
  fi
fi

circuit_breaker_triggered=0
circuit_breaker_result="none"
circuit_breaker_details="none"
if [[ "$AUTO_EXEC_ENABLED" == "1" && -x "$CIRCUIT_BREAKER_SCRIPT" ]]; then
  if [[ "$error_jobs" -ge "$CIRCUIT_BREAKER_ERROR_THRESHOLD" ]]; then
    set +e
    cb_out="$(bash "$CIRCUIT_BREAKER_SCRIPT" --error-threshold "$CIRCUIT_BREAKER_ERROR_THRESHOLD" --target-mode paused --apply 2>&1)"
    cb_rc=$?
    set -e
    circuit_breaker_triggered=1
    circuit_breaker_details="$(printf '%s' "$cb_out" | tail -n 1 | tr '\n' ' ' | tr -s ' ' | cut -c1-240)"
    if [[ "$cb_rc" -eq 1 ]]; then
      circuit_breaker_result="done"
    elif [[ "$cb_rc" -eq 2 ]]; then
      circuit_breaker_result="failed"
    else
      circuit_breaker_result="noop"
    fi
  fi
fi

queue_ready_items=0
if [[ -f "$PRIORITY_QUEUE_FILE" ]]; then
  queue_ready_items="$(jq '[.items[]? | select((.state // "") == "READY")] | length' "$PRIORITY_QUEUE_FILE" 2>/dev/null || echo 0)"
fi
if [[ ! "$queue_ready_items" =~ ^[0-9]+$ ]]; then
  queue_ready_items=0
fi

if [[ -n "$ADMIN_AGENTS_SUMMARY_OVERRIDE" ]]; then
  admin_agents_last_summary="$ADMIN_AGENTS_SUMMARY_OVERRIDE"
else
  admin_agents_cron_id_runtime="$(resolve_cron_id_by_name "$ADMIN_AGENTS_CRON_NAME" "$cron_json")"
  admin_agents_cron_id_source="name_lookup"
  if [[ -z "$admin_agents_cron_id_runtime" ]]; then
    admin_agents_cron_id_runtime="$ADMIN_AGENTS_CRON_ID"
    admin_agents_cron_id_source="fallback_env"
  fi
  admin_agents_last_summary="$(latest_cron_run_summary "$admin_agents_cron_id_runtime" 1)"
fi
if [[ -z "${admin_agents_cron_id_runtime:-}" ]]; then
  admin_agents_cron_id_runtime="none"
fi
if [[ -z "${admin_agents_cron_id_source:-}" ]]; then
  admin_agents_cron_id_source="override"
fi
admin_agents_blocked=0
admin_agents_signal_status="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*status=\([A-Z]*\).*/\1/p' | head -n 1)"
admin_agents_next_action="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*next_action=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_issue="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*deterministic_issue=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_exec_report="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*exec_report=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_issues_report="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*issues=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_suggestions_report="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*suggestions=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_action_id="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*action_id=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_action_owner="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*action_owner=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_action_scope="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*action_scope=\([^ ]*\).*/\1/p' | head -n 1)"
admin_action_id_missing=0
if printf '%s\n' "$admin_agents_last_summary" | rg -q 'status=(BLOCKED|ERROR)'; then
  admin_agents_blocked=1
elif printf '%s\n' "$admin_agents_last_summary" | rg -q 'status=WARN'; then
  if [[ -n "$admin_agents_issue" && "$admin_agents_issue" != "none" ]]; then
    admin_agents_blocked=1
  fi
fi
if [[ -z "$admin_agents_action_id" ]]; then
  admin_agents_action_id="none"
fi
if [[ "$admin_agents_blocked" -eq 1 && "$admin_agents_action_id" == "none" ]]; then
  admin_action_id_missing=1
fi
if [[ -z "$admin_agents_action_owner" ]]; then
  admin_agents_action_owner="none"
fi
if [[ -z "$admin_agents_action_scope" ]]; then
  admin_agents_action_scope="none"
fi
if [[ -z "$admin_agents_exec_report" ]]; then
  admin_agents_exec_report="none"
fi
if [[ -z "$admin_agents_issues_report" ]]; then
  admin_agents_issues_report="none"
fi
if [[ -z "$admin_agents_suggestions_report" ]]; then
  admin_agents_suggestions_report="none"
fi
admin_issue_benign_when_no_ready=0
if [[ "$queue_ready_items" -eq 0 ]]; then
  case "$admin_agents_issue" in
    none|sessions_stale_no_recent_runner_activity|roles_disabled_admins_only_mode|role_jobs_missing|role_jobs_disabled|sessions_missing|sessions_idle_generic_prompt)
      admin_issue_benign_when_no_ready=1
      ;;
  esac
fi
if [[ "$admin_agents_blocked" -eq 1 && "$admin_issue_benign_when_no_ready" -eq 1 ]]; then
  admin_agents_blocked=0
fi
admin_action_owner_external=0
case "$admin_agents_action_owner" in
  admin-agents|clawsentinel)
    admin_action_owner_external=1
    ;;
esac

unhealthy_compact="$(printf '%s' "$cron_json" \
  | jq -r '[.jobs[] | select((.state.lastStatus!=null) and (.state.lastStatus!="ok") and (.state.lastStatus!="running")) | "\(.name):\(.state.lastStatus)"] | if length==0 then "none" else join(",") end')"
if [[ "$admin_agents_blocked" -eq 1 ]]; then
  admin_agents_signal="attention_signal"
  if [[ "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ]]; then
    admin_agents_signal="blocked_signal"
  fi
  if [[ "$unhealthy_compact" == "none" ]]; then
    unhealthy_compact="admin-agents-supervisor-15m:${admin_agents_signal}"
  else
    unhealthy_compact="${unhealthy_compact},admin-agents-supervisor-15m:${admin_agents_signal}"
  fi
fi

verdict="PASS"
status="DONE"
delta="monitor_tick_ok"
blocker_id="NONE"
risks="none"
next="continuer monitoring haute fréquence et traiter uniquement les jobs en erreur"
admin_action_result="$stale_auto_exec_result"
admin_action_details="$stale_auto_exec_details"
admin_action_repeat=0
if [[ "$queue_ready_items" -eq 0 ]]; then
  delta="monitor_no_ready_queue"
  next="aucun batch READY; garder admins actifs et attendre prochain dispatch"
fi
if [[ "$error_jobs" -gt 0 ]]; then
  verdict="GO_WITH_CAUTION"
  status="IN_PROGRESS"
  delta="errors_detected"
  blocker_id="CRON_ERRORS_PRESENT"
  risks="certains jobs cron en erreur récente"
  next="prioriser force-run ciblé sur les jobs en erreur puis vérifier la récupération"
fi
if [[ "$stale_running_jobs" -gt 0 ]]; then
  verdict="GO_WITH_CAUTION"
  status="IN_PROGRESS"
  delta="stale_running_detected"
  blocker_id="CRON_STALE_RUNNING_STATE"
  risks="jobs role en etat running prolonge, risque de desynchronisation scheduler"
  next="reset jobs stale puis relancer planner/backend/frontend"
fi
if [[ "$error_jobs" -ge 3 ]]; then
  verdict="BLOCKED"
  status="BLOCKED"
  blocker_id="CRON_MULTI_ERRORS"
  risks="dégradation multi-jobs, risque de non-livraison MVP"
  next="ouvrir intervention admin immédiate (lock+backup+fix+validation)"
fi
if [[ "$circuit_breaker_triggered" -eq 1 ]]; then
  verdict="BLOCKED"
  status="BLOCKED"
  delta="circuit_breaker_triggered"
  blocker_id="ORCHESTRATION_CIRCUIT_BREAKER"
  risks="circuit breaker active suite erreur cron multi-jobs"
  next="stabiliser erreurs puis reactiver graduellement (admins-only -> sequential -> parallel)"
fi
if [[ "$stale_running_jobs" -ge 3 ]]; then
  verdict="BLOCKED"
  status="BLOCKED"
  delta="stale_running_multi"
  blocker_id="CRON_STALE_RUNNING_MULTI"
  risks="plusieurs jobs role sont bloques en running sans progression exploitable"
  next="reset stale jobs en lot puis valider reprise avec runs planner/backend/frontend"
fi
if [[ "$admin_agents_blocked" -eq 1 ]]; then
  verdict="GO_WITH_CAUTION"
  status="IN_PROGRESS"
  delta="admin_agents_attention_signal"
  blocker_id="ADMIN_AGENTS_ATTENTION_REQUIRED"
  risks="admin-agents a remonte un signal de qualite/efficacite"
  next="lire le dernier summary admin-agents, appliquer la next_action puis revalider"
  if [[ "$admin_action_id_missing" -eq 1 ]]; then
    verdict="BLOCKED"
    status="BLOCKED"
    delta="admin_signal_contract_invalid"
    blocker_id="ADMIN_SIGNAL_ACTION_ID_MISSING"
    risks="signal admin-agents sans action_id, dedupe/routage non fiables"
    next="faire corriger le contrat admin-agents (action_id/action_owner/action_scope obligatoires)"
  fi
  if [[ "$admin_action_owner_external" -eq 1 ]]; then
    reset_action_stall_counter
    delta="admin_handoff_external_owner"
    blocker_id="ADMIN_HANDOFF_PENDING"
    risks="action en attente de prise en charge par ${admin_agents_action_owner}"
    next="router action admin-agents vers ${admin_agents_action_owner} puis confirmer l'ack dans ADMIN_TEAM_ITERATIONS"
    if [[ -n "$admin_agents_next_action" ]]; then
      next="handoff ${admin_agents_action_owner}: ${admin_agents_next_action}"
    fi
    route_handoff_to_chat "$admin_agents_action_owner" "$admin_agents_issue" "${admin_agents_next_action:-none}" "${admin_agents_action_id:-none}" "${admin_agents_action_scope:-none}"
    admin_action_result="routed"
    admin_action_details="handoff_to_${admin_agents_action_owner}"
    if [[ "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ]]; then
      delta="admin_handoff_external_owner_urgent"
      risks="admin-agents signale un blocage et owner=${admin_agents_action_owner} doit intervenir rapidement"
      blocker_id="ADMIN_HANDOFF_PENDING"
    fi
  else
    action_key="${admin_agents_next_action}|${admin_agents_issue}"
    admin_action_repeat="$(update_action_stall_counter "$action_key")"
    if [[ ! "$admin_action_repeat" =~ ^[0-9]+$ ]]; then
      admin_action_repeat=1
    fi
    if [[ -n "$admin_agents_next_action" ]]; then
      next="appliquer next_action admin-agents: ${admin_agents_next_action}"
    fi
    if [[ "$AUTO_EXEC_ENABLED" == "1" && -n "$admin_agents_next_action" && "$admin_agents_action_owner" == "adminapp-codex" ]]; then
      cooldown_exempt=0
      if [[ "$admin_agents_next_action" == reset_stale_running_role_jobs* ]]; then
        cooldown_exempt=1
      fi
      if [[ "$cooldown_exempt" -eq 0 ]]; then
        if action_cooldown_active "$admin_agents_next_action"; then
          admin_action_result="cooldown"
          admin_action_details="skip_recently_executed"
        else
          execute_admin_action "$admin_agents_next_action"
          admin_action_result="$ACTION_EXEC_RESULT"
          admin_action_details="$ACTION_EXEC_DETAILS"
          mark_action_executed_now "$admin_agents_next_action"
          if [[ "$admin_action_result" == "done" ]]; then
            next="auto_exec_done:${admin_agents_next_action}; attendre recheck admin-agents"
          elif [[ "$admin_action_result" == "failed" ]]; then
            next="auto_exec_failed:${admin_agents_next_action}; recheck puis escalade si repetition"
          elif [[ "$admin_action_result" == "unsupported" ]]; then
            next="auto_exec_unsupported:${admin_agents_next_action}; intervention manuelle adminapp"
          fi
        fi
      else
        execute_admin_action "$admin_agents_next_action"
        admin_action_result="$ACTION_EXEC_RESULT"
        admin_action_details="$ACTION_EXEC_DETAILS"
        mark_action_executed_now "$admin_agents_next_action"
        if [[ "$admin_action_result" == "done" ]]; then
          next="auto_exec_done:${admin_agents_next_action}; attendre recheck admin-agents"
        elif [[ "$admin_action_result" == "failed" ]]; then
          next="auto_exec_failed:${admin_agents_next_action}; recheck puis escalade si repetition"
        elif [[ "$admin_action_result" == "unsupported" ]]; then
          next="auto_exec_unsupported:${admin_agents_next_action}; intervention manuelle adminapp"
        fi
      fi
    fi
    if [[ "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ]]; then
      delta="admin_agents_blocked_signal"
      blocker_id="ADMIN_AGENTS_NO_DELIVERY_EVIDENCE"
      risks="admin-agents signale absence de preuve de livraison"
      next="forcer une action admin-agents avec preuve (chat+iterations), puis revalider"
      if [[ -n "$admin_agents_next_action" ]]; then
        next="admin-agents blocked, appliquer next_action: ${admin_agents_next_action}"
      fi
    fi
    if [[ "$admin_action_repeat" -ge 2 && "$admin_action_result" != "done" && ( "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ) ]]; then
      verdict="BLOCKED"
      status="BLOCKED"
      delta="admin_agents_action_stalled"
      blocker_id="ADMIN_AGENTS_ACTION_REPEAT_2_TICKS"
      risks="meme issue/action remontee par admin-agents sur >=2 ticks consecutifs"
      next="escalade manuelle immediate: executer ${admin_agents_next_action:-action_inconnue} puis journaliser preuve de resolution"
    fi
  fi
else
  reset_action_stall_counter
fi

ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
tmux_line="[adminapp-codex-cron ${ts_local}] jobs=${total_jobs} ok=${ok_jobs} running=${running_jobs} pending=${pending_jobs} error=${error_jobs} timeouts=${timeout_jobs} unhealthy=${unhealthy_compact}"
tmux send-keys -t "${SESSION}:${WINDOW}" "printf '%s\n' \"$tmux_line\"" C-m

alert_fingerprint="${verdict}|errors=${error_jobs}|timeouts=${timeout_jobs}|unhealthy=${unhealthy_compact}"
last_alert=""
if [[ -f "$LAST_ALERT_FILE" ]]; then
  last_alert="$(cat "$LAST_ALERT_FILE" 2>/dev/null || true)"
fi
if [[ "$verdict" != "PASS" && "$alert_fingerprint" != "$last_alert" && -f "$CHAT_FILE" ]]; then
  printf -- "- [%s] [adminapp-codex] TYPE: ALERT MSG: cron monitor tick => verdict=%s, errors=%s, timeouts=%s, unhealthy=%s. NEXT: %s.\n" \
    "$ts_local" "$verdict" "$error_jobs" "$timeout_jobs" "$unhealthy_compact" "$next" >> "$CHAT_FILE"
fi
printf '%s\n' "$alert_fingerprint" > "$LAST_ALERT_FILE"

# Persist a compact admin memory line (no stdout noise).
append_admin_memory() {
  local ts="$1"; shift
  local line="$*"
  if [[ -z "$line" ]]; then
    return 0
  fi
  local issues="none"
  local suggestions="none"
  local stream_id="none"
  local task_id="none"
  local next_action="ADMINAPP_CRON_TICK_$(date +%Y%m%d%H%M%S)"

  if [[ -n "${admin_agents_issues_report:-}" && "${admin_agents_issues_report}" != "none" ]]; then
    issues="${admin_agents_issues_report}"
  fi
  if [[ -n "${admin_agents_suggestions_report:-}" && "${admin_agents_suggestions_report}" != "none" ]]; then
    suggestions="${admin_agents_suggestions_report}"
  fi
  if [[ -n "${admin_agents_action_owner:-}" ]]; then
    stream_id="${admin_agents_action_owner}"
  fi
  if [[ -n "${admin_agents_action_id:-}" ]]; then
    task_id="${admin_agents_action_id}"
  fi

  if command -v python3 >/dev/null 2>&1 && [[ -f "scripts/role_memory_append.py" ]]; then
    local tmp=""
    tmp="$(mktemp)"
    {
      printf 'STATUS: %s\n' "$status"
      printf 'DELTA: %s\n' "$delta"
      printf 'VERDICT: %s\n' "$verdict"
      printf 'BLOCKER_ID: %s\n' "$blocker_id"
      printf 'NEXT_ACTION_UNIQUE: %s\n' "$next_action"
      printf 'EVIDENCE: stream_id=%s; task_id=%s; exec_report=%s; issues=%s; suggestions=%s; risks=%s; next=%s; admin_agents_signal=%s\n' \
        "$stream_id" \
        "$task_id" \
        "$(printf '%s' "$line" | tr -d '\r' | tr '\n' ' ' | tr ';' ',' | tr -s ' ')" \
        "$issues" \
        "$suggestions" \
        "$risks" \
        "${next}"
    } > "$tmp"
    python3 scripts/role_memory_append.py \
      "adminapp-codex" \
      "adminapp-cron" \
      "$tmp" \
      "$ADMIN_MEMORY_FILE" \
      "$ADMIN_MEMORY_LOCK_FILE" \
      "$ts" >/dev/null 2>&1 || true
    rm -f "$tmp"
    return 0
  fi

  if command -v flock >/dev/null 2>&1; then
    {
      exec 9>"$ADMIN_MEMORY_LOCK_FILE"
      flock -x 9
      if [[ ! -f "$ADMIN_MEMORY_FILE" ]]; then
        printf '# adminapp-codex\n\n' > "$ADMIN_MEMORY_FILE"
      fi
      printf -- "- [%s] %s\n" "$ts" "$line" >> "$ADMIN_MEMORY_FILE"
      python3 - "$ADMIN_MEMORY_FILE" <<'PY' 2>/dev/null || true
import sys
from pathlib import Path
p=Path(sys.argv[1])
lines=p.read_text(encoding='utf-8',errors='ignore').splitlines(True)
if len(lines) <= 900:
    raise SystemExit(0)
head=lines[:40]
tail=lines[-760:]
p.write_text(''.join(head+['\n']+tail),encoding='utf-8')
PY
    }
  else
    if [[ ! -f "$ADMIN_MEMORY_FILE" ]]; then
      printf '# adminapp-codex\n\n' > "$ADMIN_MEMORY_FILE"
    fi
    printf -- "- [%s] %s\n" "$ts" "$line" >> "$ADMIN_MEMORY_FILE"
  fi
}

append_admin_memory "$ts_local" "status=${status} verdict=${verdict} delta=${delta} blocker=${blocker_id} jobs_total=${total_jobs} error=${error_jobs} timeouts=${timeout_jobs} stale_running=${stale_running_jobs} unhealthy=${unhealthy_compact} queue_ready=${queue_ready_items} next=${next}"

echo "STATUS: ${status}"
echo "DELTA: ${delta}"
echo "EVIDENCE: jobs_total=${total_jobs}; ok=${ok_jobs}; running=${running_jobs}; pending=${pending_jobs}; error=${error_jobs}; timed_out=${timeout_jobs}; stale_running=${stale_running_jobs}; stale_running_skipped_live=${stale_running_skipped_live}; unhealthy=${unhealthy_compact}; queue_ready=${queue_ready_items}; circuit_breaker_triggered=${circuit_breaker_triggered}; circuit_breaker_result=${circuit_breaker_result}; circuit_breaker_details=${circuit_breaker_details}; admin_agents_cron_name=${ADMIN_AGENTS_CRON_NAME}; admin_agents_cron_id=${admin_agents_cron_id_runtime}; admin_agents_cron_id_source=${admin_agents_cron_id_source}; admin_signal_status=${admin_agents_signal_status:-none}; admin_issue=${admin_agents_issue:-none}; admin_exec_report=${admin_agents_exec_report:-none}; admin_issues=${admin_agents_issues_report:-none}; admin_suggestions=${admin_agents_suggestions_report:-none}; admin_issue_benign_no_ready=${admin_issue_benign_when_no_ready}; admin_action_id=${admin_agents_action_id:-none}; admin_action_id_missing=${admin_action_id_missing}; admin_action_owner=${admin_agents_action_owner:-none}; admin_action_scope=${admin_agents_action_scope:-none}; admin_action_owner_external=${admin_action_owner_external}; admin_action_result=${admin_action_result}; admin_action_details=${admin_action_details}; admin_action_repeat=${admin_action_repeat}"
echo "RISKS: ${risks}"
echo "NEXT: ${next}"
echo "VERDICT: ${verdict}"
echo "BLOCKER_ID: ${blocker_id}"
echo "NEXT_ACTION_UNIQUE: ADMINAPP_CRON_TICK_$(date +%Y%m%d%H%M%S)"
