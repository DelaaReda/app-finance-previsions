#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd -P)"
MOD="${ROOT}/platform/automation/runner/role_routing.sh"

# shellcheck source=/dev/null
source "$MOD"

assert_eq() {
  local got="$1"
  local want="$2"
  local name="$3"
  if [[ "$got" != "$want" ]]; then
    echo "assert_fail:${name}:got=${got}:want=${want}" >&2
    exit 1
  fi
}

assert_eq "$(runner_normalize_role planner 0)" "planner" "planner_identity"
assert_eq "$(runner_normalize_role planner_architect_orchestrator 0)" "planner" "planner_orchestrator_alias"
assert_eq "$(runner_normalize_role vision-architect-tasks-planner 0)" "planner" "vision_alias"
assert_eq "$(runner_normalize_role backend_engineer 0)" "app-dev" "backend_alias"
assert_eq "$(runner_normalize_role dev 0)" "app-dev" "dev_alias"
assert_eq "$(runner_normalize_role qa 0)" "verifier" "qa_alias"
assert_eq "$(runner_normalize_role infra_engineer 0)" "admin" "infra_alias"
assert_eq "$(runner_normalize_role scrum_master 0 advisory)" "scrum_master" "scrum_advisory_kept"
assert_eq "$(runner_normalize_role scrum_master 1 advisory)" "scrum_master" "scrum_advisory_enabled"
assert_eq "$(runner_normalize_role scrum_master 0 operational)" "scrum_master" "scrum_operational_enabled"

runner_is_supported_role planner
runner_is_supported_role planner_architect_orchestrator
runner_is_supported_role app-dev
runner_is_supported_role verifier
runner_is_supported_role admin
runner_is_supported_role scrum_master
if runner_is_supported_role qa; then
  echo "assert_fail:qa_not_supported" >&2
  exit 1
fi

echo "runner_role_routing:PASS"
