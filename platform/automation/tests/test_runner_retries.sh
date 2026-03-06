#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd -P)"
MOD="${ROOT}/platform/automation/runner/retries.sh"

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

assert_eq "$(runner_normalize_seconds 15 60 10 120)" "15" "normalize_valid"
assert_eq "$(runner_normalize_seconds bad 60 10 120)" "60" "normalize_invalid"
assert_eq "$(runner_normalize_seconds 1 60 10 120)" "60" "normalize_below"
assert_eq "$(runner_normalize_seconds 900 60 10 120)" "120" "normalize_above"

assert_eq "$(runner_retry_backoff_seconds 1 5 120)" "5" "backoff_1"
assert_eq "$(runner_retry_backoff_seconds 2 5 120)" "10" "backoff_2"
assert_eq "$(runner_retry_backoff_seconds 6 5 120)" "120" "backoff_cap"

echo "runner_retries:PASS"
