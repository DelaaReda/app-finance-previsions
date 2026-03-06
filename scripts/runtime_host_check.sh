#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
RUNTIME_HOST_GUARD="${SCRIPT_DIR}/../platform/automation/lib/runtime_host_guard.sh"

if [[ ! -f "$RUNTIME_HOST_GUARD" ]]; then
  echo "Missing runtime host guard: $RUNTIME_HOST_GUARD" >&2
  exit 2
fi

# shellcheck source=/dev/null
source "$RUNTIME_HOST_GUARD"

KIND="$(fc_runtime_host_kind)"
EXPECTED="$(fc_runtime_workspace_expected)"
OS_NAME="$(uname -s 2>/dev/null || printf 'unknown')"
HOST_NAME="$(hostname 2>/dev/null || printf 'unknown')"
IS_VM=0
if fc_runtime_is_vm; then
  IS_VM=1
fi

cat <<EOF
runtime_host_kind=${KIND}
runtime_is_vm=${IS_VM}
os=${OS_NAME}
hostname=${HOST_NAME}
pwd=${PWD}
expected_workspace=${EXPECTED}
EOF
