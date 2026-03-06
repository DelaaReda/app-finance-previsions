#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
RUNTIME_HOST_GUARD="${SCRIPT_DIR}/../platform/automation/lib/runtime_host_guard.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
if [[ ! -f "$RUNTIME_HOST_GUARD" ]]; then
  echo "Missing runtime host guard: $RUNTIME_HOST_GUARD" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"
# shellcheck source=/dev/null
source "$RUNTIME_HOST_GUARD"
fc_runtime_assert_vm_or_exit "po_scrum_master_run_now"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
RUNNER="${ROOT}/platform/automation/cron_tmux_role_runner.sh"
REPORT_FILE="${ROOT}/docs/ops/PO_SCRUM_MASTER_REPORTS.md"

if [[ ! -f "$RUNNER" ]]; then
  echo "Missing runner: $RUNNER" >&2
  exit 2
fi

mkdir -p "$(dirname "$REPORT_FILE")"
if [[ ! -f "$REPORT_FILE" ]]; then
  {
    echo "# PO Scrum Master Reports"
    echo
    echo "_Runs manuels advisory (investigation + communication ciblée)._"
    echo
  } > "$REPORT_FILE"
fi

export TMUX_ROLE_ENABLE_PO_SCRUM_MASTER=1
export FC_ENABLE_PO_SCRUM_MASTER=1
export FC_PO_SCRUM_MASTER_RUN_NOW=1
export ADMIN_ROLE="${ADMIN_ROLE:-po_scrum_master}"
export AGENT_MESSAGE_BUS_ENABLED="${AGENT_MESSAGE_BUS_ENABLED:-1}"
export AGENT_MESSAGE_BUS_FILE="${AGENT_MESSAGE_BUS_FILE:-${ROOT}/docs/ops/AGENT_MESSAGE_BUS.jsonl}"
export PO_SCRUM_MASTER_ALLOW_BUS_POST="${PO_SCRUM_MASTER_ALLOW_BUS_POST:-1}"
export PO_SCRUM_MASTER_MAX_POSTS_PER_TICK="${PO_SCRUM_MASTER_MAX_POSTS_PER_TICK:-2}"
export PO_SCRUM_MASTER_POST_COOLDOWN_S="${PO_SCRUM_MASTER_POST_COOLDOWN_S:-600}"
export ROLE_ALLOW_FILE_EDITS="${ROLE_ALLOW_FILE_EDITS:-0}"

cd "$ROOT"
echo "[po_scrum_master] run-now start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
exec bash "$RUNNER" scrum_master "$@"
