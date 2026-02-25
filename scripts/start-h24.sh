#!/usr/bin/env bash
set -euo pipefail

VM_HOST="${VM_HOST:-192.168.64.9}"
VM_USER="${VM_USER:-venom}"
VM_TARGET="${VM_TARGET:-${VM_USER}@${VM_HOST}}"
OPENCLAW_UNIT="${OPENCLAW_UNIT:-openclaw-gateway}"

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/openclaw-h24"
PID_FILE="${STATE_DIR}/caffeinate.pid"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_TOOLS="${ROOT_DIR}/scripts/openclaw_vm_tools.sh"

usage() {
  cat <<USAGE
Usage: $(basename "$0") <up|down|status>

Commands:
  up      Keep Mac awake + start OpenClaw in VM + open SSH tunnel to UI
  down    Stop tunnel + stop local caffeinate process
  status  Show local keep-awake, tunnel, and VM OpenClaw status

Env overrides:
  VM_HOST, VM_USER, VM_TARGET, OPENCLAW_UNIT
USAGE
}

ensure_state_dir() {
  mkdir -p "${STATE_DIR}"
}

is_caffeinate_alive() {
  [[ -f "${PID_FILE}" ]] || return 1
  local pid
  pid="$(cat "${PID_FILE}")"
  [[ -n "${pid}" ]] || return 1
  ps -p "${pid}" -o command= 2>/dev/null | grep -q 'caffeinate'
}

start_caffeinate() {
  ensure_state_dir
  if is_caffeinate_alive; then
    echo "caffeinate: already running (pid $(cat "${PID_FILE}"))"
    return 0
  fi
  nohup caffeinate -dimsu >/dev/null 2>&1 &
  echo "$!" >"${PID_FILE}"
  echo "caffeinate: started (pid $!)"
}

stop_caffeinate() {
  if ! is_caffeinate_alive; then
    rm -f "${PID_FILE}"
    echo "caffeinate: not running"
    return 0
  fi
  local pid
  pid="$(cat "${PID_FILE}")"
  kill "${pid}" >/dev/null 2>&1 || true
  rm -f "${PID_FILE}"
  echo "caffeinate: stopped"
}

vm_bootstrap() {
  echo "vm: checking OpenClaw on ${VM_TARGET}"
  ssh -o ConnectTimeout=8 "${VM_TARGET}" "bash -lc '
set -e
if command -v loginctl >/dev/null 2>&1; then
  linger=\$(loginctl show-user \"\$USER\" -p Linger --value 2>/dev/null || echo unknown)
  echo \"vm: linger=\$linger\"
fi
systemctl --user enable --now ${OPENCLAW_UNIT} >/dev/null 2>&1 || true
systemctl --user is-active ${OPENCLAW_UNIT} >/dev/null 2>&1 && echo \"vm: ${OPENCLAW_UNIT}=active\" || echo \"vm: ${OPENCLAW_UNIT}=inactive\"
openclaw status --plain | sed -n \"1,40p\"
'"
}

tunnel_up() {
  if [[ -x "${VM_TOOLS}" ]]; then
    VM_HOST="${VM_TARGET}" "${VM_TOOLS}" up
  else
    echo "warning: ${VM_TOOLS} not found/executable; tunnel not started"
  fi
}

tunnel_down() {
  if [[ -x "${VM_TOOLS}" ]]; then
    VM_HOST="${VM_TARGET}" "${VM_TOOLS}" down || true
  fi
}

show_status() {
  if is_caffeinate_alive; then
    echo "caffeinate: running (pid $(cat "${PID_FILE}"))"
  else
    echo "caffeinate: stopped"
  fi
  if [[ -x "${VM_TOOLS}" ]]; then
    VM_HOST="${VM_TARGET}" "${VM_TOOLS}" status || true
  fi
}

cmd="${1:-}"
case "${cmd}" in
  up)
    start_caffeinate
    vm_bootstrap
    tunnel_up
    ;;
  down)
    tunnel_down
    stop_caffeinate
    ;;
  status)
    show_status
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    usage
    exit 1
    ;;
esac
