#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
LOCK_FILE="${FC_ROLE_RECOVERY_LOCK_FILE:-/tmp/fc-codex-role-recovery.lock}"
LOCK_META_FILE="${FC_ROLE_RECOVERY_LOCK_META_FILE:-${LOCK_FILE}.meta}"
LOCK_STALE_SECONDS="${FC_ROLE_RECOVERY_LOCK_STALE_SECONDS:-1800}"
MAX_RUNTIME_SECONDS="${FC_ROLE_RECOVERY_MAX_SECONDS:-480}"
VERIFY_ATTEMPTS="${FC_ROLE_RECOVERY_VERIFY_ATTEMPTS:-5}"
VERIFY_SLEEP_SECONDS="${FC_ROLE_RECOVERY_VERIFY_SLEEP_SECONDS:-2}"
LOG_DIR="${FC_ROLE_RECOVERY_LOG_DIR:-$ROOT/logs-codex-runs}"
LOG_FILE="${FC_ROLE_RECOVERY_LOG_FILE:-$LOG_DIR/role-recovery.log}"
TOPOLOGY_FILE="${FC_ROLE_TOPOLOGY_FILE:-$ROOT/logs-codex-runs/orchestrator-state/parallel-role-topology-active.json}"
LANE_VALIDITY_SCRIPT="${ROOT}/platform/automation/lane_validity.py"
LANE_VALIDITY_PROOF_MAX_AGE_SECONDS="${FC_LANE_PRODUCTIVE_PROOF_MAX_AGE_SECONDS:-1800}"
LANE_VALIDITY_SUMMARY_JSON=""
ROLES=()
RUN_STARTED_EPOCH="$(date +%s)"

load_roles_from_topology() {
  local topology_roles=()
  local role=""
  if [[ ! -f "$TOPOLOGY_FILE" ]] || ! command -v jq >/dev/null 2>&1; then
    return 1
  fi
  mapfile -t topology_roles < <(
    jq -r '.roles[]? | select((.role // "") != "") | .role' "$TOPOLOGY_FILE" 2>/dev/null || true
  )
  if [[ "${#topology_roles[@]}" -eq 0 ]]; then
    return 1
  fi
  for role in "${topology_roles[@]}"; do
    if [[ -n "$role" ]]; then
      ROLES+=("$role")
    fi
  done
  return 0
}

normalize_role_list() {
  local line=""
  line="$(printf '%s\n' "${ROLES[@]}" | awk 'NF {print}' | sort -u)"
  mapfile -t ROLES < <(printf '%s\n' "$line" 2>/dev/null || true)
}

cleanup_stale_runtime_locks() {
  local role_state_dir="${HOME}/.openclaw/cron/role-state"
  local shared_lock_dir="${ROOT}/.tmp/openclaw-shared-locks"
  local cleanup_script="${ROOT}/scripts/cleanup_stale_role_locks.sh"
  local stale_min="${FC_STALE_LOCK_MINUTES:-20}"
  if [[ -f "$cleanup_script" ]]; then
    FC_STALE_LOCK_MINUTES="$stale_min" \
    FC_STALE_LOCK_LOG="$LOG_FILE" \
    FC_ROLE_STATE_DIR="$role_state_dir" \
    FC_RUNTIME_LOCK_DIR="/tmp/fc-agent-locks" \
    bash "$cleanup_script" >/dev/null 2>&1 || true
  else
    find /tmp/fc-agent-locks -name '*.lock' -mmin +20 -delete 2>/dev/null || true
    if [[ -d "$role_state_dir" ]]; then
      find "$role_state_dir" -name '*.run.lock' -mmin +20 -delete 2>/dev/null || true
      find "$role_state_dir" -name '*.memory.lock' -mmin +20 -delete 2>/dev/null || true
    fi
  fi
  if [[ -d "$shared_lock_dir" ]]; then
    find "$shared_lock_dir" -name '*.lock' -mmin +30 -delete 2>/dev/null || true
  fi
}

if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
  for fallback in \
    "/home/venom/analyse-financiere/logs-codex-runs" \
    "${HOME}/.cache/fc/logs-codex-runs"
  do
    if mkdir -p "$fallback" 2>/dev/null; then
      LOG_DIR="$fallback"
      break
    fi
  done
  LOG_FILE="${FC_ROLE_RECOVERY_LOG_FILE:-$LOG_DIR/role-recovery.log}"
  printf '%s [WARN] log dir fallback applied root=%s log_dir=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$ROOT" "$LOG_DIR" >> "$LOG_FILE"
fi

ts() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

role_recovery_runtime_guard() {
  local now elapsed
  now="$(date +%s)"
  elapsed=$((now - RUN_STARTED_EPOCH))
  if [[ "$elapsed" -gt "$MAX_RUNTIME_SECONDS" ]]; then
    printf '%s [ERROR] runtime_guard_exceeded elapsed=%ss limit=%ss\n' "$(ts)" "$elapsed" "$MAX_RUNTIME_SECONDS" >> "$LOG_FILE"
    exit 124
  fi
}

lock_holder_pid() {
  local pid=""
  if command -v lsof >/dev/null 2>&1; then
    pid="$(lsof -t "$LOCK_FILE" 2>/dev/null | head -n 1 || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pid="$(fuser "$LOCK_FILE" 2>/dev/null | awk '{print $1}' | head -n 1 || true)"
  fi
  printf '%s' "$pid"
}

lock_meta_started_epoch() {
  local started="0"
  if [[ -f "$LOCK_META_FILE" ]]; then
    started="$(awk -F= '/^started_epoch=/{print $2}' "$LOCK_META_FILE" 2>/dev/null | head -n 1 || true)"
  fi
  if [[ ! "$started" =~ ^[0-9]+$ ]]; then
    started="0"
  fi
  printf '%s' "$started"
}

write_lock_meta() {
  local now now_iso
  now="$(date +%s)"
  now_iso="$(ts)"
  cat >"$LOCK_META_FILE" <<EOF
pid=$$
started_epoch=$now
started_iso=$now_iso
root=$ROOT
EOF
}

cleanup_lock_meta() {
  rm -f "$LOCK_META_FILE" >/dev/null 2>&1 || true
}

role_session_name() {
  local session=""

  if [[ -f "$TOPOLOGY_FILE" ]] && command -v jq >/dev/null 2>&1; then
    session="$(jq -r --arg r "$1" '.roles[]? | select(.role==$r) | .session_name // empty' "$TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
    if [[ -n "$session" && "$session" != "null" ]]; then
      printf '%s\n' "$session"
      return 0
    fi
  fi

  case "$1" in
    planner) echo "codex_planner_cron" ;;
    admin) echo "codex_admin_cron" ;;
    backend_engineer) echo "codex_backend_engineer_cron" ;;
    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
    dev) echo "codex_dev_cron" ;;
    tester) echo "codex_tester_cron" ;;
    integrator) echo "codex_integrator_cron" ;;
    data_analyst) echo "codex_data_analyst_cron" ;;
    infra_engineer) echo "codex_infra_engineer_cron" ;;
    analyst) echo "codex_analyst_cron" ;;
    qa) echo "codex_qa_cron" ;;
    architect) echo "codex_architect_cron" ;;
    po) echo "codex_po_cron" ;;
    scrum_master) echo "codex_scrum_master_cron" ;;
    clawsentinel) echo "clawsentinel" ;;
    *) return 1 ;;
  esac
}

pane_current_command() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]'
}

pane_current_path() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_current_path}" 2>/dev/null
}

pane_pid() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_pid}" 2>/dev/null | tr -d '[:space:]'
}

session_tail() {
  local target="$1"
  tmux capture-pane -p -t "$target" -S -20 2>/dev/null || true
}

session_has_interactive_codex_prompt() {
  local target="$1"
  local tail=""
  tail="$(session_tail "$target")"
  [[ "$tail" == *"Update now (runs \`npm install -g @openai/codex\`)"* ]] && return 0
  [[ "$tail" == *"Press enter to continue"* ]] && return 0
  [[ "$tail" == *"Trust this project"* ]] && return 0
  [[ "$tail" == *"Allow all file"* ]] && return 0
  [[ "$tail" == *"Switch to "* && "$tail" == *"lower credit"* ]] && return 0
  return 1
}

session_path_invalid() {
  local target="$1"
  local path=""
  local pid=""
  local child_pids=""
  local child_pid=""
  path="$(pane_current_path "$target" || true)"
  if fc_workspace_runtime_path_invalid "$path" "$ROOT"; then
    return 0
  fi

  pid="$(pane_pid "$target" || true)"
  if fc_pid_workspace_invalid "$pid" "$ROOT"; then
    return 0
  fi

  if [[ "$pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    child_pids="$(pgrep -P "$pid" 2>/dev/null || true)"
    while IFS= read -r child_pid; do
      [[ "$child_pid" =~ ^[0-9]+$ ]] || continue
      if fc_pid_workspace_invalid "$child_pid" "$ROOT"; then
        return 0
      fi
    done <<< "$child_pids"
  fi

  return 1
}

session_invalid_reason() {
  local session="$1"
  local target="${session}:0.0"
  local path=""
  local cmd=""
  local pid=""
  local child_pids=""
  local child_pid=""

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "missing_session"
    return 0
  fi

  path="$(pane_current_path "$target" || true)"
  if [[ -z "$path" ]]; then
    echo "missing_workdir"
    return 0
  fi
  if [[ "$path" == *"(deleted)"* ]]; then
    echo "deleted_workdir"
    return 0
  fi
  if fc_workspace_runtime_path_invalid "$path" "$ROOT"; then
    echo "foreign_workdir"
    return 0
  fi
  pid="$(pane_pid "$target" || true)"
  if fc_pid_workspace_invalid "$pid" "$ROOT"; then
    echo "foreign_workdir"
    return 0
  fi
  if [[ "$pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    child_pids="$(pgrep -P "$pid" 2>/dev/null || true)"
    while IFS= read -r child_pid; do
      [[ "$child_pid" =~ ^[0-9]+$ ]] || continue
      if fc_pid_workspace_invalid "$child_pid" "$ROOT"; then
        echo "foreign_workdir"
        return 0
      fi
    done <<< "$child_pids"
  fi
  if session_has_interactive_codex_prompt "$target"; then
    echo "interactive_prompt"
    return 0
  fi

  cmd="$(pane_current_command "$target" || true)"
  case "$cmd" in
    bash|sh|zsh|fish)
      echo "shell_only"
      ;;
    "")
      echo "missing_pane_command"
      ;;
    *)
      echo "session_not_ready"
      ;;
  esac
}

session_is_auxiliary_candidate() {
  local session="$1"
  case "$session" in
    codex_*_cron|qwen_*_cron|adminapp_codex_sync|admin-agents-sync-cron|clawsentinel)
      return 0
      ;;
  esac
  return 1
}

quarantine_invalid_unmapped_sessions() {
  local -n mapped_ref=$1
  local session=""
  local reason=""
  local count=0
  local -a sessions=()
  mapfile -t sessions < <(tmux list-sessions -F '#S' 2>/dev/null || true)
  for session in "${sessions[@]}"; do
    session_is_auxiliary_candidate "$session" || continue
    [[ -n "${mapped_ref[$session]:-}" ]] && continue
    reason="$(session_invalid_reason "$session" || true)"
    case "$reason" in
      deleted_workdir|foreign_workdir|missing_workdir|interactive_prompt)
        printf '%s [ACTION] quarantine invalid auxiliary session=%s reason=%s\n' "$(ts)" "$session" "$reason" >> "$LOG_FILE"
        tmux kill-session -t "$session" >/dev/null 2>&1 || true
        count=$((count + 1))
        ;;
    esac
  done
  printf '%s' "$count"
}

dismiss_interactive_codex_prompt() {
  return 1
}

preseed_codex_version_dismissal() {
  local version_file="${HOME}/.codex/version.json"
  [[ -f "$version_file" ]] || return 0
  python3 - "$version_file" <<'PY' >/dev/null 2>&1 || true
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
try:
    payload = json.loads(path.read_text())
except Exception:
    raise SystemExit(0)
latest = payload.get("latest_version")
if not latest:
    raise SystemExit(0)
if payload.get("dismissed_version") == latest:
    raise SystemExit(0)
payload["dismissed_version"] = latest
path.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
PY
}

refresh_lane_validity_summary() {
  [[ -n "$LANE_VALIDITY_SUMMARY_JSON" ]] && return 0
  [[ -f "$LANE_VALIDITY_SCRIPT" ]] || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  LANE_VALIDITY_SUMMARY_JSON="$(python3 "$LANE_VALIDITY_SCRIPT" summary --root "$ROOT" --roles "$(IFS=,; echo "${ROLES[*]}")" --proof-max-age "$LANE_VALIDITY_PROOF_MAX_AGE_SECONDS" 2>/dev/null || true)"
  [[ -n "$LANE_VALIDITY_SUMMARY_JSON" ]]
}

role_canonical_recovery_reason() {
  local role="$1"
  refresh_lane_validity_summary || return 0
  LANE_VALIDITY_SUMMARY_JSON="$LANE_VALIDITY_SUMMARY_JSON" python3 - "$role" <<'PY'
import json, os, sys

role = sys.argv[1].strip().lower()
try:
    payload = json.loads(os.environ.get("LANE_VALIDITY_SUMMARY_JSON", "") or "{}")
except Exception:
    raise SystemExit(0)
roles = payload.get("roles", {}) if isinstance(payload, dict) else {}
row = roles.get(role, {}) if isinstance(roles, dict) else {}
if not isinstance(row, dict) or not row.get("needs_recovery"):
    raise SystemExit(0)
reason = str(row.get("reason", "canonical_invalid")).strip() or "canonical_invalid"
task_ids = row.get("actionable_task_ids", [])
task_ids = ",".join(str(item).strip() for item in task_ids[:3] if str(item).strip()) or "none"
batch_ids = payload.get("active_batches", []) if isinstance(payload, dict) else []
batch = str(batch_ids[0]).strip() if batch_ids else "none"
print(f"{reason} batch={batch} tasks={task_ids}")
PY
}

session_ready() {
  local session="$1"
  local target="${session}:0.0"
  local cmd=""
  local pid=""
  local children=""
  local tail=""

  if ! tmux has-session -t "$session" 2>/dev/null; then
    return 1
  fi
  if session_path_invalid "$target"; then
    return 1
  fi
  if session_has_interactive_codex_prompt "$target"; then
    return 1
  fi

  cmd="$(pane_current_command "$target" || true)"
  tail="$(session_tail "$target")"
  if [[ "$cmd" == *"codex"* || "$cmd" == *"qwen"* || "$cmd" == "node" ]]; then
    return 0
  fi
  if [[ "$cmd" == "bash" || "$cmd" == "sh" || "$cmd" == "zsh" || "$cmd" == "fish" ]]; then
    if [[ "$tail" == *"[READY] Session active"* || "$tail" == *"OpenAI Codex"* || "$tail" == *"/model to change"* || "$tail" == *"Update now (runs "* ]]; then
      return 1
    fi
  fi

  pid="$(pane_pid "$target" || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    children="$(pgrep -P "$pid" -af 2>/dev/null || true)"
    if printf '%s\n' "$children" | grep -Eiq '(codex|qwen|node.*codex|openai.*codex)'; then
      return 0
    fi
  fi
  return 1
}

start_or_restart_session() {
  local session="$1"
  local target="${session}:0.0"
  local launch_cmd=""
  local session_model="${FC_ROLE_SESSION_MODEL:-gpt-5.4}"
  local session_thinking="${FC_ROLE_SESSION_THINKING:-high}"

  tmux start-server >/dev/null 2>&1 || true
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session" >/dev/null 2>&1 || true
  fi
  preseed_codex_version_dismissal
  printf -v launch_cmd 'cd %q && unset NO_COLOR && if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi; export COLORTERM="${COLORTERM:-truecolor}"; export FORCE_COLOR="${FORCE_COLOR:-1}"; exec codex --model %q -c %q --cd %q --no-alt-screen' "$ROOT" "$session_model" "model_reasoning_effort=\"${session_thinking}\"" "$ROOT"
  # Do not let the recovery flock FD leak into tmux. If tmux inherits FD 9,
  # it keeps /tmp/fc-codex-role-recovery.lock open after the script exits and
  # every later recovery run sees a false "already running" state.
  exec 9>&-
  tmux new-session -d -s "$session" -c "$ROOT" "bash -lc $(printf '%q' "$launch_cmd")"
  exec 9>"$LOCK_FILE"
  flock -n 9 || true
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  sleep 2
  dismiss_interactive_codex_prompt "$target" || true
  sleep 1
  if ! session_ready "$session"; then
    tmux send-keys -t "$target" C-c >/dev/null 2>&1 || true
    tmux send-keys -t "$target" "cd $ROOT" C-m >/dev/null 2>&1 || true
    preseed_codex_version_dismissal
    tmux send-keys -t "$target" "codex --model $session_model -c 'model_reasoning_effort=\"$session_thinking\"' --cd $ROOT --no-alt-screen" C-m >/dev/null 2>&1 || true
    sleep 2
    dismiss_interactive_codex_prompt "$target" || true
    sleep 1
  fi
}

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    holder_pid="$(lock_holder_pid)"
    started_epoch="$(lock_meta_started_epoch)"
    now_epoch="$(date +%s)"
    age_s=0
    if [[ "$started_epoch" -gt 0 ]]; then
      age_s=$((now_epoch - started_epoch))
      if [[ "$age_s" -lt 0 ]]; then
        age_s=0
      fi
    fi
    if [[ "$holder_pid" =~ ^[0-9]+$ ]] && [[ "$age_s" -ge "$LOCK_STALE_SECONDS" ]] && [[ "${FC_ROLE_RECOVERY_KILL_STALE_LOCK_PID:-1}" == "1" ]]; then
      printf '%s [WARN] stale lock holder detected pid=%s age_s=%s threshold_s=%s; attempting terminate\n' "$(ts)" "$holder_pid" "$age_s" "$LOCK_STALE_SECONDS" >> "$LOG_FILE"
      kill -TERM "$holder_pid" >/dev/null 2>&1 || true
      sleep 2
      if kill -0 "$holder_pid" >/dev/null 2>&1; then
        kill -KILL "$holder_pid" >/dev/null 2>&1 || true
      fi
      sleep 1
      if ! flock -n 9; then
        printf '%s [SKIP] auto-recovery already running lock_pid=%s age_s=%s\n' "$(ts)" "${holder_pid:-unknown}" "$age_s" >> "$LOG_FILE"
        exit 0
      fi
      printf '%s [INFO] stale lock released; continuing recovery\n' "$(ts)" >> "$LOG_FILE"
    else
      printf '%s [SKIP] auto-recovery already running lock_pid=%s age_s=%s\n' "$(ts)" "${holder_pid:-unknown}" "$age_s" >> "$LOG_FILE"
      exit 0
    fi
  fi
  write_lock_meta
  trap cleanup_lock_meta EXIT
else
  LOCK_DIR_FALLBACK="${LOCK_FILE}.dirlock"
  if ! mkdir "$LOCK_DIR_FALLBACK" 2>/dev/null; then
    printf '%s [SKIP] auto-recovery already running (mkdir lock fallback)\n' "$(ts)" >> "$LOG_FILE"
    exit 0
  fi
  trap 'rmdir "$LOCK_DIR_FALLBACK" >/dev/null 2>&1 || true' EXIT
fi

cd "$ROOT"
role_recovery_runtime_guard
cleanup_stale_runtime_locks

if ! command -v tmux >/dev/null 2>&1; then
  printf '%s [ERROR] tmux missing in PATH\n' "$(ts)" >> "$LOG_FILE"
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  printf '%s [ERROR] codex missing in PATH\n' "$(ts)" >> "$LOG_FILE"
  exit 2
fi

if ! load_roles_from_topology; then
  ROLES=("planner" "dev" "admin")
fi
normalize_role_list
declare -A recovery_reasons=()
declare -A mapped_sessions=()

down_roles=()
for role in "${ROLES[@]}"; do
  role_recovery_runtime_guard
  session="$(role_session_name "$role")"
  if [[ -z "$session" ]]; then
    printf '%s [WARN] no session mapping for role=%s; skip\n' "$(ts)" "$role" >> "$LOG_FILE"
    continue
  fi
  mapped_sessions["$session"]=1
  if ! session_ready "$session"; then
    down_roles+=("$role")
    recovery_reasons["$role"]="$(session_invalid_reason "$session" || true)"
    [[ -n "${recovery_reasons[$role]:-}" ]] || recovery_reasons["$role"]="session_not_ready"
    continue
  fi
  canonical_reason="$(role_canonical_recovery_reason "$role" || true)"
  if [[ -n "$canonical_reason" ]]; then
    down_roles+=("$role")
    recovery_reasons["$role"]="canonical_${canonical_reason}"
  fi
done

auxiliary_quarantined="$(quarantine_invalid_unmapped_sessions mapped_sessions)"

if [[ ${#down_roles[@]} -eq 0 ]]; then
  if [[ "${auxiliary_quarantined:-0}" =~ ^[0-9]+$ ]] && [[ "${auxiliary_quarantined:-0}" -gt 0 ]]; then
    printf '%s [OK] no core recovery needed; quarantined invalid auxiliary sessions=%s\n' "$(ts)" "$auxiliary_quarantined" >> "$LOG_FILE"
    exec 9>&- 2>/dev/null || true
    exit 0
  fi
  printf '%s [OK] no recovery needed; all mapped roles already UP\n' "$(ts)" >> "$LOG_FILE"
  exec 9>&- 2>/dev/null || true
  exit 0
fi

printf '%s [WARN] detected DOWN role(s): %s\n' "$(ts)" "$(IFS=,; echo "${down_roles[*]}")" >> "$LOG_FILE"
for role in "${down_roles[@]}"; do
  role_recovery_runtime_guard
  session="$(role_session_name "$role")"
  if [[ -z "$session" ]]; then
    printf '%s [WARN] no session mapping for role=%s; skip restart\n' "$(ts)" "$role" >> "$LOG_FILE"
    continue
  fi
  printf '%s [ACTION] restart role=%s session=%s reason=%s\n' "$(ts)" "$role" "$session" "${recovery_reasons[$role]:-session_not_ready}" >> "$LOG_FILE"
  start_or_restart_session "$session"
done

verify_down=("${ROLES[@]}")
attempt=1
while [[ "$attempt" -le "$VERIFY_ATTEMPTS" ]]; do
  role_recovery_runtime_guard
  verify_down_next=()
  for role in "${verify_down[@]}"; do
    session="$(role_session_name "$role")"
    if [[ -z "$session" ]]; then
      continue
    fi
    if ! session_ready "$session"; then
      verify_down_next+=("$role")
    fi
  done
  verify_down=("${verify_down_next[@]}")
  if [[ ${#verify_down[@]} -eq 0 ]]; then
    break
  fi
  if [[ "$attempt" -lt "$VERIFY_ATTEMPTS" ]]; then
    sleep "$VERIFY_SLEEP_SECONDS"
  fi
  attempt=$((attempt + 1))
done

if [[ ${#verify_down[@]} -gt 0 ]]; then
  printf '%s [ERROR] recovery failed after %s attempt(s); roles still DOWN: %s\n' "$(ts)" "$VERIFY_ATTEMPTS" "$(IFS=,; echo "${verify_down[*]}")" >> "$LOG_FILE"
  exec 9>&- 2>/dev/null || true
  exit 1
fi

printf '%s [OK] recovery successful; all mapped roles are UP\n' "$(ts)" >> "$LOG_FILE"
# Explicitly close FD 9 before exit to prevent tmux from inheriting the flock FD.
# Without this, tmux keeps FD 9 open after the script exits, permanently holding
# the flock and causing every subsequent invocation to see 'already running'.
exec 9>&- 2>/dev/null || true
exit 0
