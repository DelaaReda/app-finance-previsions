#!/usr/bin/env bash
set -euo pipefail

VM_HOST="${VM_SSH_HOST:-dev-vm-utm}"
VM_USER="${VM_SSH_USER:-venom}"
VM_KEY="${VM_SSH_KEY:-/Users/venom/.ssh/id_utm_linux}"
VM_WORKDIR="${VM_SSH_WORKDIR:-/home/venom/analyse-financiere}"
VM_CONNECT_TIMEOUT="${VM_SSH_CONNECT_TIMEOUT:-8}"
SKIP_HOST_CHECK=0

usage() {
  cat <<'USAGE'
Usage: scripts/vm_ssh_exec.sh [--workdir /remote/path] [--skip-host-check] -- "<command>"

Runs a command inside the canonical VM workspace from the local Mac controller.
By default it first verifies `runtime_is_vm=1` on the remote host.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      VM_WORKDIR="$2"
      shift 2
      ;;
    --skip-host-check)
      SKIP_HOST_CHECK=1
      shift
      ;;
    --)
      shift
      break
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 2
fi

CMD="$*"

SSH_BASE=(
  ssh
  -i "$VM_KEY"
  -o BatchMode=yes
  -o ConnectTimeout="$VM_CONNECT_TIMEOUT"
  "${VM_USER}@${VM_HOST}"
)

run_remote() {
  local remote_payload="$1"
  "${SSH_BASE[@]}" "bash -lc $(printf '%q' "$remote_payload")"
}

if [[ "$SKIP_HOST_CHECK" -ne 1 ]]; then
  HOST_CHECK_CMD="cd $(printf '%q' "$VM_WORKDIR") && bash scripts/runtime_host_check.sh"
  HOST_CHECK_OUT="$(run_remote "$HOST_CHECK_CMD")" || {
    echo "[vm_ssh_exec] remote host check failed" >&2
    exit 10
  }
  if ! printf '%s\n' "$HOST_CHECK_OUT" | rg -q '^runtime_is_vm=1$'; then
    echo "[vm_ssh_exec] remote host is not the canonical VM runtime" >&2
    printf '%s\n' "$HOST_CHECK_OUT" >&2
    exit 11
  fi
fi

REMOTE_CMD="cd $(printf '%q' "$VM_WORKDIR") && ${CMD}"
exec "${SSH_BASE[@]}" "bash -lc $(printf '%q' "$REMOTE_CMD")"
