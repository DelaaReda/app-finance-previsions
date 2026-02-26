#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MONITOR_SCRIPT="$ROOT/scripts/tmux_codex_live_monitor.sh"
LOG_DIR="${TMUX_LIVE_LOG_DIR:-$ROOT/logs-codex-runs/tmux-live}"
SESSION_NAME="${TMUX_LIVE_WATCHDOG_SESSION:-tmux_live_monitor}"
MODE="${1:-status}"

usage() {
  cat <<'EOF'
Usage: tmux_live_watchdog.sh <start|stop|restart|status>

Manage a persistent tmux session running the live monitor:
  bash scripts/tmux_live_watchdog.sh start
  bash scripts/tmux_live_watchdog.sh stop
  bash scripts/tmux_live_watchdog.sh restart
  bash scripts/tmux_live_watchdog.sh status
EOF
}

ensure_prereqs() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux not found in PATH" >&2
    exit 3
  fi
  if [[ ! -x "$MONITOR_SCRIPT" ]]; then
    echo "monitor script missing or not executable: $MONITOR_SCRIPT" >&2
    exit 4
  fi
}

start_watchdog() {
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "WATCHDOG status=already_running session=${SESSION_NAME}"
    return 0
  fi
  mkdir -p "$LOG_DIR"
  tmux new-session -d -s "$SESSION_NAME" "cd '$ROOT' && bash scripts/tmux_codex_live_monitor.sh --mode follow --engine capture --include-admin"
  echo "WATCHDOG status=started session=${SESSION_NAME} log_dir=${LOG_DIR}"
}

stop_watchdog() {
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME" >/dev/null 2>&1 || true
    echo "WATCHDOG status=stopped session=${SESSION_NAME}"
  else
    echo "WATCHDOG status=already_stopped session=${SESSION_NAME}"
  fi
}

status_watchdog() {
  local running="no"
  local pane_cmd="none"
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    running="yes"
    pane_cmd="$(tmux display-message -p -t "${SESSION_NAME}:0.0" "#{pane_current_command}" 2>/dev/null || echo "unknown")"
  fi
  echo "WATCHDOG status=${running} session=${SESSION_NAME} pane_cmd=${pane_cmd} log_dir=${LOG_DIR}"
  if [[ -d "$LOG_DIR" ]]; then
    ls -lt "$LOG_DIR" 2>/dev/null | head -n 12
  fi
}

ensure_prereqs

case "$MODE" in
  start)
    start_watchdog
    ;;
  stop)
    stop_watchdog
    ;;
  restart)
    stop_watchdog
    start_watchdog
    ;;
  status)
    status_watchdog
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
