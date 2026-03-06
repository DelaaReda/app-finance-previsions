#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
MOD_MAIN="$ROOT/platform/automation/runner/main.sh"
CFG_FILE="$ROOT/platform/config/runner/runner.v1.yaml"
if [[ ! -f "$CFG_FILE" ]]; then
  CFG_FILE="$ROOT/platform/config/runner/runner_config.v1.yaml"
fi
if [[ ! -f "$CFG_FILE" ]]; then
  CFG_FILE="$ROOT/platform/automation/config/runner.v1.yaml"
fi

# shellcheck source=/dev/null
source "$MOD_MAIN"
runner_modules_init

required_funcs=(
  runner_load_config_env
  runner_normalize_role
  runner_retry_backoff_seconds
  runner_contract_is_blocked
  runner_append_trace
  runner_lock_is_stale
  runner_message_bus_enabled
  runner_tshape_has_target
  ensure_role_session_ready
  tmux_target
)

for fn in "${required_funcs[@]}"; do
  declare -F "$fn" >/dev/null 2>&1 || {
    echo "missing function: $fn" >&2
    exit 2
  }
done

if [[ -f "$CFG_FILE" ]]; then
  LOADER="$ROOT/platform/automation/runner/config_loader.py"
  if [[ ! -f "$LOADER" ]]; then
    LOADER="$ROOT/platform/automation/runner_config.py"
  fi
  runner_load_config_env "planner" "$CFG_FILE" "$LOADER" "1" "" "RUNNER_CONFIG"
  [[ -n "${RUNNER_CONFIG_VERSION:-}" ]] || {
    echo "RUNNER_CONFIG_VERSION not exported" >&2
    exit 2
  }
fi

echo "runner_modules:PASS"
