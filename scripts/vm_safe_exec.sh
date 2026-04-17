#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
VM_WORKDIR="${VM_SSH_WORKDIR:-/home/venom/analyse-financiere}"
FORCE_CONFIRM=0

usage() {
  cat <<'USAGE'
Usage: scripts/vm_safe_exec.sh [--workdir /remote/path] [--force-confirm] -- "<command>"

Runs the command safety gate on the VM and, if allowed, executes the command
through the remote exec_safe.sh wrapper inside the canonical VM workspace.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      VM_WORKDIR="$2"
      shift 2
      ;;
    --force-confirm)
      FORCE_CONFIRM=1
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
QUOTED_CMD="$(printf '%q' "$CMD")"
QUOTED_WORKDIR="$(printf '%q' "$VM_WORKDIR")"

GATE_REMOTE_CMD="python3 platform/policies/command_safety_gate.py --cmd ${QUOTED_CMD} --workdir ${QUOTED_WORKDIR}"
GATE_JSON="$(bash "${ROOT}/scripts/vm_ssh_exec.sh" --workdir "$VM_WORKDIR" -- "$GATE_REMOTE_CMD")"
DECISION="$(printf '%s' "$GATE_JSON" | python3 -c 'import sys, json; print(json.load(sys.stdin)["decision"])')"

printf '%s\n' "$GATE_JSON" >&2

if [[ "$DECISION" == "BLOCK" ]]; then
  echo "[vm_safe_exec] blocked by remote safety gate" >&2
  exit 40
fi

FORCE_FLAG=""
if [[ "$FORCE_CONFIRM" -eq 1 ]]; then
  FORCE_FLAG="--force-confirm"
fi

REMOTE_EXEC_CMD="platform/policies/exec_safe.sh ${FORCE_FLAG} --workdir ${QUOTED_WORKDIR} -- ${QUOTED_CMD}"
exec bash "${ROOT}/scripts/vm_ssh_exec.sh" --workdir "$VM_WORKDIR" -- "$REMOTE_EXEC_CMD"
