#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
ROOT_FROM_PARENT="$(cd "${SCRIPT_DIR}/.." && pwd -P 2>/dev/null || true)"
ROOT_FROM_GRANDPARENT="$(cd "${SCRIPT_DIR}/../.." && pwd -P 2>/dev/null || true)"

resolve_root() {
  local candidate_a="${1:-}"
  local candidate_b="${2:-}"
  local a="/home/venom/shared/analyse-financiere"
  local b="/home/venom/analyse-financiere"
  local candidate=""
  for candidate in "$candidate_a" "$candidate_b" "$a" "$b"; do
    if [[ -z "$candidate" ]]; then
      continue
    fi
    if [[ -d "$candidate/scripts" ]] && [[ -d "$candidate/platform" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  printf '%s\n' "$candidate_a"
}

workspace_writable() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  mkdir -p "$candidate/logs-codex-runs" >/dev/null 2>&1 || return 1
  [[ -w "$candidate/logs-codex-runs" ]]
}

ROOT="$(resolve_root "$ROOT_FROM_PARENT" "$ROOT_FROM_GRANDPARENT")"
if ! workspace_writable "$ROOT"; then
  for fallback in "/home/venom/analyse-financiere" "/home/venom/shared/analyse-financiere"; do
    if [[ "$fallback" == "$ROOT" ]]; then
      continue
    fi
    if [[ -d "$fallback/scripts" ]] && [[ -d "$fallback/platform" ]] && workspace_writable "$fallback"; then
      ROOT="$fallback"
      break
    fi
  done
fi
LOCK_FILE="${FC_ROLE_RECOVERY_LOCK_FILE:-/tmp/fc-codex-role-recovery.lock}"
LOG_DIR="${FC_ROLE_RECOVERY_LOG_DIR:-$ROOT/logs-codex-runs}"
LOG_FILE="${FC_ROLE_RECOVERY_LOG_FILE:-$LOG_DIR/role-recovery.log}"
TOPOLOGY_FILE="${FC_ROLE_TOPOLOGY_FILE:-$ROOT/docs/operations/orchestrator/parallel-role-topology-active.json}"
ROLES=()

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
  find /tmp/fc-agent-locks -name '*.lock' -mmin +20 -delete 2>/dev/null || true
  if [[ -d "$role_state_dir" ]]; then
    find "$role_state_dir" -name '*.run.lock' -mmin +20 -delete 2>/dev/null || true
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
    printf '%s [SKIP] auto-recovery already running\n' "$(ts)" >> "$LOG_FILE"
    exit 0
  fi
else
  LOCK_DIR_FALLBACK="${LOCK_FILE}.dirlock"
  if ! mkdir "$LOCK_DIR_FALLBACK" 2>/dev/null; then
    printf '%s [SKIP] auto-recovery already running (mkdir lock fallback)\n' "$(ts)" >> "$LOG_FILE"
    exit 0
  fi
  trap 'rmdir "$LOCK_DIR_FALLBACK" >/dev/null 2>&1 || true' EXIT
fi

cd "$ROOT"
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
  exit 0
fi

printf '%s [WARN] detected DOWN role(s): %s\n' "$(ts)" "$(IFS=,; echo "${down_roles[*]}")" >> "$LOG_FILE"
for role in "${down_roles[@]}"; do
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
  exit 1
fi

printf '%s [OK] recovery successful; all mapped roles are UP\n' "$(ts)" >> "$LOG_FILE"
exit 0
