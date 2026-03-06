#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
BUS_FILE_DEFAULT="${ROOT}/docs/ops/AGENT_MESSAGE_BUS.jsonl"

export AGENT_MESSAGE_BUS_FILE="${AGENT_MESSAGE_BUS_FILE:-$BUS_FILE_DEFAULT}"
export AGENT_MESSAGE_STICKY_DEFAULT="${AGENT_MESSAGE_STICKY_DEFAULT:-1}"
export AGENT_MESSAGE_DEFAULT_TTL_MIN="${AGENT_MESSAGE_DEFAULT_TTL_MIN:-10080}"
export AGENT_MESSAGE_MAX_ACTIVE_PER_ROLE="${AGENT_MESSAGE_MAX_ACTIVE_PER_ROLE:-10}"

PY_ENGINE="${SCRIPT_DIR}/agent_message_bus.py"
if [[ ! -f "$PY_ENGINE" ]]; then
  echo "Missing bus engine: $PY_ENGINE" >&2
  exit 2
fi

exec python3 "$PY_ENGINE" "$@"
