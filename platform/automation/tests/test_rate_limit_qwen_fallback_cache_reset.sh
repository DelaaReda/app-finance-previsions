#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
RUNNER="${ROOT}/automation/cron_tmux_role_runner.sh"

if [[ ! -f "$RUNNER" ]]; then
  echo "missing runner: $RUNNER" >&2
  exit 1
fi

grep -q 'TMUX_ROLE_RATE_LIMIT_QWEN_FALLBACK=0' "$RUNNER"
grep -q 'TMUX_ROLE_RATE_LIMIT_SECONDARY_ACTIVE=0' "$RUNNER"
grep -q 'TMUX_ROLE_RATE_LIMIT_CACHE_FILE=""' "$RUNNER"

echo "PASS rate_limit_qwen_fallback_cache_reset"
