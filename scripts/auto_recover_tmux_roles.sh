#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LOCK_FILE="${FC_ROLE_RECOVERY_LOCK_FILE:-/tmp/fc-codex-role-recovery.lock}"
LOG_DIR="${FC_ROLE_RECOVERY_LOG_DIR:-$ROOT/logs-codex-runs}"
LOG_FILE="${FC_ROLE_RECOVERY_LOG_FILE:-$LOG_DIR/role-recovery.log}"
ROLES=(planner dev tester qa architect po scrum_master clawsentinel)

mkdir -p "$LOG_DIR"

ts() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

role_session_name() {
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    dev) echo "codex_dev_cron" ;;
    tester) echo "codex_tester_cron" ;;
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
  if [[ "$cmd" == *"codex"* || "$cmd" == "node" ]]; then
    return 0
  fi

  pid="$(pane_pid "$target" || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    children="$(pgrep -P "$pid" -af 2>/dev/null || true)"
    if printf '%s\n' "$children" | grep -Eiq '(codex|node.*codex|openai.*codex)'; then
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

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '%s [SKIP] auto-recovery already running\n' "$(ts)" >> "$LOG_FILE"
  exit 0
fi

cd "$ROOT"

if ! command -v tmux >/dev/null 2>&1; then
  printf '%s [ERROR] tmux missing in PATH\n' "$(ts)" >> "$LOG_FILE"
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  printf '%s [ERROR] codex missing in PATH\n' "$(ts)" >> "$LOG_FILE"
  exit 2
fi

down_roles=()
for role in "${ROLES[@]}"; do
  session="$(role_session_name "$role")"
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
  printf '%s [ACTION] restart role=%s session=%s\n' "$(ts)" "$role" "$session" >> "$LOG_FILE"
  start_or_restart_session "$session"
done

verify_down=()
for role in "${ROLES[@]}"; do
  session="$(role_session_name "$role")"
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
