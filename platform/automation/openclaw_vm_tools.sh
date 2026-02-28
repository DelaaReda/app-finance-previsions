#!/usr/bin/env bash
set -euo pipefail

VM_HOST="${VM_HOST:-dev-vm-utm}"
LOCAL_PORT="${OPENCLAW_LOCAL_PORT:-18789}"
REMOTE_PORT="${OPENCLAW_REMOTE_PORT:-18789}"
SOCKET_PATH="${OPENCLAW_TUNNEL_SOCKET:-$HOME/.openclaw-vm-tunnel.sock}"

usage() {
  cat <<USAGE
Usage: $(basename "$0") <command>

Commands:
  up       Start SSH tunnel (localhost:${LOCAL_PORT} -> VM:${REMOTE_PORT})
  down     Stop SSH tunnel
  status   Show tunnel and gateway status
  ui       Open Control UI in macOS browser (starts tunnel if needed)
  logs     Tail VM gateway debug logs
  tui      Open VM OpenClaw TUI in this terminal
  doctor   Run OpenClaw doctor on VM
USAGE
}

tunnel_up() {
  if ssh -S "$SOCKET_PATH" -O check "$VM_HOST" >/dev/null 2>&1; then
    echo "Tunnel already running via socket: $SOCKET_PATH"
    return 0
  fi

  ssh -MNf \
    -S "$SOCKET_PATH" \
    -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
    "$VM_HOST"

  echo "Tunnel started: http://127.0.0.1:${LOCAL_PORT}"
}

tunnel_down() {
  if ssh -S "$SOCKET_PATH" -O check "$VM_HOST" >/dev/null 2>&1; then
    ssh -S "$SOCKET_PATH" -O exit "$VM_HOST" >/dev/null
    echo "Tunnel stopped"
  else
    echo "Tunnel is not running"
  fi
}

status() {
  if ssh -S "$SOCKET_PATH" -O check "$VM_HOST" >/dev/null 2>&1; then
    echo "Tunnel: running ($SOCKET_PATH)"
  else
    echo "Tunnel: stopped"
  fi

  if curl -fsS "http://127.0.0.1:${LOCAL_PORT}/health" >/dev/null 2>&1; then
    echo "Local UI endpoint: reachable"
  else
    echo "Local UI endpoint: not reachable"
  fi

  echo "--- VM OpenClaw status ---"
  ssh "$VM_HOST" 'openclaw channels status --probe | sed -n "1,120p"'
}

open_ui() {
  tunnel_up
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:${LOCAL_PORT}/"
  else
    echo "Open in browser: http://127.0.0.1:${LOCAL_PORT}/"
  fi
}

logs() {
  ssh "$VM_HOST" 'tail -f /home/venom/.openclaw/logs/gateway-debug.log'
}

tui() {
  ssh -t "$VM_HOST" 'openclaw tui'
}

doctor() {
  ssh "$VM_HOST" 'openclaw doctor --fix'
}

main() {
  cmd="${1:-}"
  case "$cmd" in
    up) tunnel_up ;;
    down) tunnel_down ;;
    status) status ;;
    ui) open_ui ;;
    logs) logs ;;
    tui) tui ;;
    doctor) doctor ;;
    ""|-h|--help|help) usage ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
