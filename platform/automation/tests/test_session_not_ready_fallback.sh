#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
RUNNER="${ROOT}/automation/cron_tmux_role_runner.sh"

if [[ ! -f "$RUNNER" ]]; then
  echo "missing runner: $RUNNER" >&2
  exit 1
fi

grep -q 'SESSION_NOT_READY_FALLBACK_CODEX="${TMUX_ROLE_SESSION_NOT_READY_FALLBACK_CODEX:-1}"' "$RUNNER"
grep -q 'SESSION_NOT_READY_FALLBACK_COUNT_FILE="\${STATE_DIR}/\${ROLE}\.session_not_ready_fallback_count"' "$RUNNER"
grep -q '^increment_session_not_ready_fallback_count()' "$RUNNER"
grep -q 'session_not_ready_fallback_codex role=\${ROLE} channel=\${channel} tick=\${tick} timeout=\${timeout_seconds}s count=\${fallback_count}' "$RUNNER"

echo "PASS session_not_ready_fallback_contract"
