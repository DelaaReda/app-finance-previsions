#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
FILE="${ROOT}/scripts/fc_setup_crons.sh"

# Policy: advisory cron must be full-profile only.
grep -q 'if \[\[ "\$CRON_PROFILE" != "full" \]\]; then' "$FILE"
grep -q 'PO_SCRUM_MASTER_CRON_ENABLED=0' "$FILE"

# Full profile cron line exists and runs the dedicated wrapper.
grep -q 'PO Scrum Master (advisory)' "$FILE"
grep -q 'cron_po_scrum_master_tick\.sh' "$FILE"

# Canary block should not carry explicit scrum cron entry.
awk '/if \[\[ "\$CRON_PROFILE" == "canary" \]\]; then/,/else/' "$FILE" | \
  grep -q 'ADMIN — volontairement désactivé en canary'

# default cadence requested by architecture plan.
grep -q 'PO_SCRUM_MASTER_CRON_EXPR="\${FC_PO_SCRUM_MASTER_CRON_EXPR:-3-58/5}"' "$FILE"

echo "PASS test_fc_setup_crons_po_scrum_master"
