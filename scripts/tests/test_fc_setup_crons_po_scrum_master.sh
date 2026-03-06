#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
FILE="${ROOT}/scripts/fc_setup_crons.sh"

# Planner orchestrator is now the scheduled entrypoint by default.
grep -q 'PLANNER_ORCHESTRATOR_ACTIVE=1' "$FILE"
grep -q 'PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY' "$FILE"
grep -q 'EXPERIMENTAL_PLANNER_ONLY="${FC_EXPERIMENTAL_PLANNER_ONLY:-}"' "$FILE"

# Planner-only block exists and disables independent dev/admin/scrum scheduling.
grep -q 'sole scheduled orchestrator' "$FILE"
grep -q 'planner-owned Codex subagents via planner_subagent_manager.py' "$FILE"

# Explicit planner-experimental operator profile exists.
grep -q -- '--planner-experimental' "$FILE"
grep -q 'planner-experimental' "$FILE"

# Legacy scrum wrapper still exists for manual fallback compatibility.
grep -q 'cron_scrum_master_tick\.sh' "$FILE"

# Planner cadence remains explicit.
grep -q '0,22,44 \* \* \* \* .*fc_agent_tick.sh planner' "$FILE"

echo "PASS test_fc_setup_crons_po_scrum_master"
