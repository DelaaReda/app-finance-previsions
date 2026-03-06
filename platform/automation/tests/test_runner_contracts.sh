#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd -P)"
MOD="${ROOT}/platform/automation/runner/contracts.sh"

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

payload=$'STATUS: PASS\nVERDICT: PASS\nDELTA: READY_ITEM_AVAILABLE\n'
assert_eq "$(runner_contract_value_from_text STATUS "$payload")" "PASS" "status_from_text"
assert_eq "$(runner_contract_value_from_text DELTA "$payload")" "READY_ITEM_AVAILABLE" "delta_from_text"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
printf 'STATUS: BLOCKED\nVERDICT: BLOCKED\n' > "$tmp"
assert_eq "$(runner_contract_value_from_file STATUS "$tmp")" "BLOCKED" "status_from_file"

runner_contract_is_blocked "BLOCKED" "PASS"
runner_contract_is_blocked "PASS" "BLOCKED"
if runner_contract_is_blocked "PASS" "PASS"; then
  echo "assert_fail:blocked_false_positive" >&2
  exit 1
fi

echo "runner_contracts:PASS"
