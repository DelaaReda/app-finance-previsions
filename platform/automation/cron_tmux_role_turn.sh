#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

# Deprecated entrypoint kept for compatibility.
# Canonical implementation is cron_tmux_role_runner.sh (tmux-native, no qwen_orchestrator dependency).
exec bash scripts/cron_tmux_role_runner.sh "$@"
