#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
TEST_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
ROOT="$(cd "${TEST_DIR}/../../.." && pwd -P)"
HELPER="${ROOT}/platform/automation/lib/workspace_paths.sh"

if [[ ! -f "$HELPER" ]]; then
  echo "helper_missing:$HELPER" >&2
  exit 2
fi

# shellcheck source=/dev/null
source "$HELPER"

assert_eq() {
  local got="$1"
  local want="$2"
  local label="$3"
  if [[ "$got" != "$want" ]]; then
    echo "assert_fail:${label}:got=${got}:want=${want}" >&2
    exit 1
  fi
}

assert_true() {
  local label="$1"
  shift
  if ! "$@"; then
    echo "assert_fail:${label}" >&2
    exit 1
  fi
}

assert_false() {
  local label="$1"
  shift
  if "$@"; then
    echo "assert_fail:${label}:expected_false" >&2
    exit 1
  fi
}

assert_true "layout_repo" fc_workspace_has_layout "$ROOT"
assert_true "writable_repo" fc_workspace_writable "$ROOT"

resolved_from_env="$(FC_WORKSPACE_ROOT="$ROOT" fc_resolve_workspace_root "/tmp")"
if [[ "$ROOT" == "/home/venom/shared/analyse-financiere" ]]; then
  assert_eq "$resolved_from_env" "/home/venom/analyse-financiere" "env_precedence_prefers_vm_canonical"
else
  assert_eq "$resolved_from_env" "$ROOT" "env_precedence"
fi

resolved_from_scripts="$(fc_resolve_workspace_root "${ROOT}/scripts")"
if [[ "$ROOT" == "/home/venom/shared/analyse-financiere" ]]; then
  assert_eq "$resolved_from_scripts" "/home/venom/analyse-financiere" "scripts_parent_prefers_vm_canonical"
else
  assert_eq "$resolved_from_scripts" "$ROOT" "scripts_parent"
fi

tmp_ws="$(mktemp -d)"
trap 'rm -rf "$tmp_ws"' EXIT
mkdir -p "$tmp_ws/scripts" "$tmp_ws/platform"
resolved_tmp="$(FC_WORKSPACE_ROOT="$tmp_ws" fc_resolve_workspace_root "/tmp")"
assert_eq "$resolved_tmp" "$tmp_ws" "tmp_workspace_layout"

preferred="$(fc_prefer_writable_workspace "$ROOT")"
if [[ "$ROOT" == "/home/venom/shared/analyse-financiere" ]]; then
  assert_eq "$preferred" "/home/venom/analyse-financiere" "prefer_current_writable_prefers_vm_canonical"
else
  assert_eq "$preferred" "$ROOT" "prefer_current_writable"
fi

assert_false "shared_runtime_path_is_valid" \
  fc_workspace_runtime_path_invalid "/home/venom/shared/analyse-financiere" "/home/venom/analyse-financiere"
assert_false "shared_runtime_subpath_is_valid" \
  fc_workspace_runtime_path_invalid "/home/venom/shared/analyse-financiere/platform" "/home/venom/analyse-financiere"

echo "workspace_paths:PASS"
