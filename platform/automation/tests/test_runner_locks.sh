#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd -P)"
MOD="${ROOT}/platform/automation/runner/locks.sh"

# shellcheck source=/dev/null
source "$MOD"

meta="$(mktemp)"
trap 'rm -f "$meta"' EXIT
start_old=$(( $(date +%s) - 2000 ))
printf 'pid=123 start_epoch=%s role=dev\n' "$start_old" > "$meta"

age="$(runner_lock_age_seconds "$meta")"
if ! [[ "$age" =~ ^[0-9]+$ ]]; then
  echo "assert_fail:age_not_numeric:${age}" >&2
  exit 1
fi
if (( age < 1000 )); then
  echo "assert_fail:age_too_small:${age}" >&2
  exit 1
fi

if ! runner_lock_is_stale "$meta" 900; then
  echo "assert_fail:expected_stale" >&2
  exit 1
fi
if runner_lock_is_stale "$meta" 999999; then
  echo "assert_fail:unexpected_stale" >&2
  exit 1
fi

echo "runner_locks:PASS"
