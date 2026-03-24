#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

checks_total=0
checks_ok=0
declare -a failures=()

check_ok() {
  checks_total=$((checks_total + 1))
  checks_ok=$((checks_ok + 1))
  printf 'CHECK_OK %s\n' "$1"
}

check_fail() {
  checks_total=$((checks_total + 1))
  failures+=("$1")
  printf 'CHECK_FAIL %s\n' "$1"
}

check_file_exists() {
  local target="$1"
  if [[ -f "$target" ]]; then
    check_ok "file:${target}"
  else
    check_fail "file_missing:${target}"
  fi
}

check_openclaw_config_true() {
  local key="$1"
  local value=""
  value="$(openclaw config get "$key" 2>/dev/null || true)"
  if [[ "$value" == "true" ]]; then
    check_ok "openclaw_config:${key}=true"
  else
    check_fail "openclaw_config:${key}=${value:-UNSET}"
  fi
}

OPENCLAW_BIN=""
OPENCLAW_VERSION="unknown"
SKILLS_OUTPUT=""

WORKBOARD_VALIDATE_FILE="${WORKBOARD_VALIDATE_FILE:-logs-codex-runs/orchestrator-state/parallel-workstreams-plumbing.json}"

if command -v openclaw >/dev/null 2>&1; then
  OPENCLAW_BIN="$(command -v openclaw)"
  OPENCLAW_VERSION="$(openclaw --version 2>/dev/null || echo "unknown")"
  check_ok "openclaw_bin=${OPENCLAW_BIN}"
  check_ok "openclaw_version=${OPENCLAW_VERSION}"
else
  check_fail "openclaw_missing_in_PATH"
fi

if [[ -n "$OPENCLAW_BIN" ]]; then
  check_openclaw_config_true "browser.enabled"
  check_openclaw_config_true "tools.web.search.enabled"
  check_openclaw_config_true "tools.web.fetch.enabled"

  cdp_url="$(openclaw config get browser.cdpUrl 2>/dev/null || true)"
  if [[ "$cdp_url" =~ ^https?://|^wss?:// ]]; then
    check_ok "openclaw_config:browser.cdpUrl=${cdp_url}"
  else
    check_fail "openclaw_config:browser.cdpUrl=${cdp_url:-UNSET}"
  fi

  if SKILLS_OUTPUT="$(openclaw skills check --json 2>/dev/null)"; then
    check_ok "openclaw_skills_check=ok"
    for skill in api-tester test-runner finance-regression-gate debug-pro tmux codex-orchestration browser-smoke repo-scan runtime-triage delivery-proof-check; do
      if printf '%s\n' "$SKILLS_OUTPUT" | python3 -c 'import json,sys; obj=json.load(sys.stdin); ready={entry.get("name") for entry in obj.get("ready", []) if isinstance(entry, dict)}; missing={entry.get("name") for entry in obj.get("missing", []) if isinstance(entry, dict)}; skill=sys.argv[1]; raise SystemExit(0 if skill in ready and skill not in missing else 1)' "$skill"; then
        check_ok "skill_ready:${skill}"
      else
        check_fail "skill_missing_or_unavailable:${skill}"
      fi
    done
  else
    check_fail "openclaw_skills_check_failed"
  fi
fi

check_file_exists "scripts/exec_safe.sh"
check_file_exists "scripts/backend_regression_gate.sh"
check_file_exists "scripts/run_delivery_gate.sh"
check_file_exists "platform/policies/validate_batch_state.py"
check_file_exists "platform/automation/compat/projections/parallel_workstream.py"
check_file_exists "scripts/cron_tmux_role_runner.sh"

if bash -n scripts/cron_tmux_role_runner.sh; then
  check_ok "bash_syntax:cron_tmux_role_runner"
else
  check_fail "bash_syntax:cron_tmux_role_runner"
fi

if python3 -m py_compile platform/automation/compat/projections/parallel_workstream.py; then
  check_ok "python_compile:parallel_workstream"
else
  check_fail "python_compile:parallel_workstream"
fi

if python3 -m py_compile platform/policies/validate_batch_state.py; then
  check_ok "python_compile:validate_batch_state"
else
  check_fail "python_compile:validate_batch_state"
fi

validate_output=""
if validate_output="$(python3 platform/automation/compat/projections/parallel_workstream.py --board "$WORKBOARD_VALIDATE_FILE" validate --queue logs-codex-runs/orchestrator-state/priority-queue.json --require-proof-manifest 2>&1)"; then
  if printf '%s\n' "$validate_output" | rg -q "INV-QUEUE-CLOSED-WITH-OPEN-TASKS"; then
    check_fail "workboard_validate=queue_closed_with_open_tasks"
  else
    check_ok "workboard_validate=require_proof_manifest"
  fi
else
  check_fail "workboard_validate=require_proof_manifest"
fi

failed=$((checks_total - checks_ok))
printf 'DEV_QA_TOOLING_SUMMARY total=%s ok=%s failed=%s openclaw_bin=%s openclaw_version=%s\n' \
  "$checks_total" "$checks_ok" "$failed" "${OPENCLAW_BIN:-missing}" "${OPENCLAW_VERSION}"

if [[ "$failed" -gt 0 ]]; then
  IFS=,
  printf 'DEV_QA_TOOLING_BLOCKERS %s\n' "${failures[*]}"
  echo "VERDICT: BLOCKED"
  exit 2
fi

echo "VERDICT: PASS"
