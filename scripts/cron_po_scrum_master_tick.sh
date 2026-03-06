#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

export FC_ENABLE_PO_SCRUM_MASTER="${FC_ENABLE_PO_SCRUM_MASTER:-1}"
export FC_PO_SCRUM_MASTER_CRON="${FC_PO_SCRUM_MASTER_CRON:-1}"
export FC_PO_SCRUM_MASTER_RUN_NOW="${FC_PO_SCRUM_MASTER_RUN_NOW:-1}"
exec bash "$ROOT/scripts/cron_scrum_master_tick.sh"
