#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
GUARD="${ROOT}/platform/policies/role_contract_guard.py"
RUNNER="${ROOT}/platform/automation/cron_tmux_role_runner.sh"

# Runner hardening markers for scrum auto intents / receipts.
grep -q "FC_SCRUM_AUTO_INTENTS_HARDENED" "${RUNNER}"
grep -q "scrum_auto_intents_error" "${RUNNER}"
grep -q "agent_msg_intent_skip" "${RUNNER}"

# Advisory scrum should never hard-block on missing artifact alone.
workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT
payload_file="${workdir}/payload.txt"
cat > "${payload_file}" <<'PAYLOAD'
STATUS: WAIT
DELTA: NO_DELTA
EVIDENCE: task_update=analysis_only; lock_check=ok; run_note=scrum advisory audit sans artifact explicite pour e2e guard
RISKS: low
NEXT: owner=scrum_master; action=publish advisory
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: SCRUM_ADVISORY_NO_BLOCK_E2E
PAYLOAD

out="$(FC_SCRUM_MASTER_MODE=advisory FC_SCRUM_ARTIFACT_AUTOFILL=1 python3 "${GUARD}" scrum_master primary "${payload_file}" 0 0 0 qv-e2e wv-e2e)"
printf '%s\n' "${out}" | rg -q '^STATUS: (IN_PROGRESS|WAIT)$'
printf '%s\n' "${out}" | rg -q '^VERDICT: GO_WITH_CAUTION$'
printf '%s\n' "${out}" | rg -q '^BLOCKER_ID: NONE$'
printf '%s\n' "${out}" | rg -q 'scrum_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md'

echo "PASS test_scrum_advisory_no_block_e2e"
