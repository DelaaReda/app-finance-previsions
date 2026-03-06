#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
BUS_SCRIPT="${ROOT}/platform/automation/agent_message_bus.sh"

if [[ ! -x "$BUS_SCRIPT" ]]; then
  echo "Missing bus script: $BUS_SCRIPT" >&2
  exit 2
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <message_id> [reason | --reason <text>]" >&2
  exit 2
fi

message_id="$1"
shift || true

reason="closed_by_operator"
if [[ $# -ge 2 && "${1:-}" == "--reason" ]]; then
  reason="${2:-closed_by_operator}"
elif [[ $# -ge 1 ]]; then
  reason="$*"
fi

exec "$BUS_SCRIPT" close --id "$message_id" --reason "$reason"
