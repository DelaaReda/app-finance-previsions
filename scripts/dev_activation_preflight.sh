#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="$SCRIPT_DIR/../platform/automation/lib/workspace_paths.sh"
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"
ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"

bash "$ROOT/scripts/runtime_host_check.sh" >/dev/null

exec python3 "$ROOT/platform/automation/dev_activation_readiness.py" --root "$ROOT" --write-report "$@"
