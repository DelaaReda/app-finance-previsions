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
LOG_DIR="${FC_ROLE_RECOVERY_LOG_DIR:-$ROOT/logs-codex-runs}"
LOG_FILE="${FC_ROLE_RECOVERY_LOG_FILE:-$LOG_DIR/role-recovery.log}"
TOPOLOGY_FILE="${FC_ROLE_TOPOLOGY_FILE:-$ROOT/docs/operations/orchestrator/parallel-role-topology-active.json}"
ROLES=()
RUN_STARTED_EPOCH="$(date +%s)"

if [[ ! -f "$TOPOLOGY_FILE" ]]; then
  TOPOLOGY_FILE="$ROOT/docs/orchestrator-ops/parallel-role-topology-active.json"
fi

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
    "/home/venom/shared/analyse-financiere/logs-codex-runs" \
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

pane_pid() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_pid}" 2>/dev/null | tr -d '[:space:]'
}

session_ready() {
  local session="$1"
  local target="${session}:0.0"
  local cmd=""
  local pid=""
  local children=""

  if ! tmux has-session -t "$session" 2>/dev/null; then
    return 1
  fi

  cmd="$(pane_current_command "$target" || true)"
  # Codex/Qwen can run as transient child processes. An idle shell pane is still a
  # healthy role session and should not be force-restarted.
  if [[ "$cmd" == *"codex"* || "$cmd" == *"qwen"* || "$cmd" == "node" ]]; then
    return 0
  fi
  if [[ "$cmd" == "bash" || "$cmd" == "sh" || "$cmd" == "zsh" || "$cmd" == "fish" ]]; then
    return 0
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

  tmux start-server >/dev/null 2>&1 || true
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session" >/dev/null 2>&1 || true
  fi
  printf -v launch_cmd 'cd %q && unset NO_COLOR && if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi; export COLORTERM="${COLORTERM:-truecolor}"; export FORCE_COLOR="${FORCE_COLOR:-1}"; exec codex --no-alt-screen' "$ROOT"
  tmux new-session -d -s "$session" "bash -lc $(printf '%q' "$launch_cmd")"
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  sleep 2
  if ! session_ready "$session"; then
    tmux send-keys -t "$target" C-c >/dev/null 2>&1 || true
    tmux send-keys -t "$target" "cd $ROOT" C-m >/dev/null 2>&1 || true
    tmux send-keys -t "$target" "codex --no-alt-screen" C-m >/dev/null 2>&1 || true
    sleep 2
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

down_roles=()
for role in "${ROLES[@]}"; do
  role_recovery_runtime_guard
  session="$(role_session_name "$role")"
  if [[ -z "$session" ]]; then
    printf '%s [WARN] no session mapping for role=%s; skip\n' "$(ts)" "$role" >> "$LOG_FILE"
    continue
  fi
  if ! session_ready "$session"; then
    down_roles+=("$role")
  fi
done

if [[ ${#down_roles[@]} -eq 0 ]]; then
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
  printf '%s [ACTION] restart role=%s session=%s\n' "$(ts)" "$role" "$session" >> "$LOG_FILE"
  start_or_restart_session "$session"
done

verify_down=()
for role in "${ROLES[@]}"; do
  role_recovery_runtime_guard
  session="$(role_session_name "$role")"
  if [[ -z "$session" ]]; then
    continue
  fi
  if ! session_ready "$session"; then
    verify_down+=("$role")
  fi
done

if [[ ${#verify_down[@]} -gt 0 ]]; then
  printf '%s [ERROR] recovery failed; roles still DOWN: %s\n' "$(ts)" "$(IFS=,; echo "${verify_down[*]}")" >> "$LOG_FILE"
  exec 9>&- 2>/dev/null || true
  exit 1
fi

printf '%s [OK] recovery successful; all mapped roles are UP\n' "$(ts)" >> "$LOG_FILE"
# Explicitly close FD 9 before exit to prevent tmux from inheriting the flock FD.
# Without this, tmux keeps FD 9 open after the script exits, permanently holding
# the flock and causing every subsequent invocation to see 'already running'.
exec 9>&- 2>/dev/null || true
exit 0
