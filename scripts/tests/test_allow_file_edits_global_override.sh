#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
RUNNER_FILE="${ROOT}/platform/automation/cron_tmux_role_runner.sh"
TICK_FILE="${ROOT}/scripts/fc_agent_tick.sh"
SCRUM_WRAPPER="${ROOT}/scripts/cron_po_scrum_master_tick.sh"

# Global override flag must exist and default to enabled.
grep -q 'FC_FORCE_ALLOW_FILE_EDITS_ALL="${FC_FORCE_ALLOW_FILE_EDITS_ALL:-1}"' "$RUNNER_FILE"
grep -q 'FC_FORCE_ALLOW_FILE_EDITS_ALL="${FC_FORCE_ALLOW_FILE_EDITS_ALL:-1}"' "$TICK_FILE"

# Runtime override trace and force behavior must exist in runner.
grep -q '\[ALLOW_FILE_EDITS_OVERRIDE\]' "$RUNNER_FILE"
grep -q 'if \[\[ "${FC_FORCE_ALLOW_FILE_EDITS_ALL}" == "1" \]\]; then' "$RUNNER_FILE"
grep -q 'ROLE_ALLOW_FILE_EDITS_EFFECTIVE=1' "$RUNNER_FILE"

# Rollback path must be present.
grep -q '^else$' "$RUNNER_FILE"

# scrum wrappers should no longer default to read-only.
grep -q 'export ROLE_ALLOW_FILE_EDITS="${ROLE_ALLOW_FILE_EDITS:-1}"' "$SCRUM_WRAPPER"
grep -q 'export ROLE_ALLOW_FILE_EDITS="${ROLE_ALLOW_FILE_EDITS:-$DEFAULT_ROLE_ALLOW_FILE_EDITS}"' "$TICK_FILE"

echo "PASS test_allow_file_edits_global_override"
