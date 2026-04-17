#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
RUNNER="${ROOT}/automation/cron_tmux_role_runner.sh"

if [[ ! -f "$RUNNER" ]]; then
  echo "missing runner: $RUNNER" >&2
  exit 1
fi

grep -q 'TMUX_ROLE_PLANNER_IDLE_AUTOBATCH_ALLOW_ACTIVE_QUEUED="${TMUX_ROLE_PLANNER_IDLE_AUTOBATCH_ALLOW_ACTIVE_QUEUED:-0}"' "$RUNNER"
grep -q 'if \[\[ "\$TMUX_ROLE_PLANNER_IDLE_AUTOBATCH_ALLOW_ACTIVE_QUEUED" == "1" \]\]; then' "$RUNNER"

if grep -q 'planner-autobatch --queue .* --allow-active-queued"' "$RUNNER"; then
  echo "planner autobatch still allows active queued by default" >&2
  exit 1
fi

echo "PASS planner_autobatch_no_active_queued_by_default"
