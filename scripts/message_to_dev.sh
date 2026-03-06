#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
BUS_SCRIPT="${ROOT}/platform/automation/agent_message_bus.sh"

if [[ ! -x "$BUS_SCRIPT" ]]; then
  echo "Missing bus script: $BUS_SCRIPT" >&2
  exit 2
fi

msg="${1:-}"
shift || true
if [[ -z "$msg" ]]; then
  echo "Usage: $0 "'<message>'" [--id MSG_...] [--priority normal|high|urgent] [--ttl-min <n>]" >&2
  exit 2
fi

"$BUS_SCRIPT" post --targets dev --msg "$msg" "$@"
