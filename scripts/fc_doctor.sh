#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"
if [[ -n "${PWD:-}" ]] && fc_workspace_has_layout "$PWD" && fc_workspace_writable "$PWD"; then
  ROOT="$PWD"
else
  ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
fi
if [[ "${FC_DOCTOR_LEGACY:-0}" == "1" ]]; then
  PY="${ROOT}/platform/automation/doctor.py"
else
  PY="${ROOT}/platform/automation/fc_doctor.py"
fi
if [[ ! -f "$PY" && "${FC_DOCTOR_LEGACY:-0}" != "1" ]]; then
  PY="${ROOT}/platform/automation/doctor.py"
fi

if [[ ! -f "$PY" ]]; then
  echo "Missing doctor script: $PY" >&2
  exit 2
fi

exec python3 "$PY" --root "$ROOT" "$@"
