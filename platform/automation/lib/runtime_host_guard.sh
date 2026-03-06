#!/usr/bin/env bash

# Runtime host guard helpers.
# Policy: orchestration/services must run inside the VM workspace.

fc_runtime_workspace_expected() {
  printf '%s\n' "${FC_RUNTIME_WORKSPACE_ROOT:-/home/venom/analyse-financiere}"
}

fc_runtime_host_kind() {
  local forced="${FC_RUNTIME_HOST_KIND:-}"
  local os=""
  local host=""
  local expected=""

  if [[ -n "$forced" ]]; then
    printf '%s\n' "$forced"
    return 0
  fi

  os="$(uname -s 2>/dev/null || printf 'unknown')"
  host="$(hostname 2>/dev/null || printf 'unknown')"
  expected="$(fc_runtime_workspace_expected)"

  case "$os" in
    Darwin)
      printf '%s\n' "mac_host"
      return 0
      ;;
    Linux)
      if [[ -d "${expected}/scripts" && -d "${expected}/platform" ]]; then
        printf '%s\n' "vm_runtime"
        return 0
      fi
      if [[ "$host" == *"Apple-Virtualization-Generic-Platform"* ]]; then
        printf '%s\n' "vm_runtime"
        return 0
      fi
      if [[ "${PWD:-}" == /home/venom/analyse-financiere* || "${PWD:-}" == /home/venom/shared/analyse-financiere* ]]; then
        printf '%s\n' "vm_runtime"
        return 0
      fi
      printf '%s\n' "linux_host"
      return 0
      ;;
    *)
      printf '%s\n' "unknown_host"
      return 0
      ;;
  esac
}

fc_runtime_is_vm() {
  [[ "$(fc_runtime_host_kind)" == "vm_runtime" ]]
}

fc_runtime_assert_vm_or_exit() {
  local caller="${1:-runtime}"
  local expected=""
  local kind=""
  local os=""

  if [[ "${FC_ALLOW_LOCAL_MAC:-0}" == "1" ]]; then
    return 0
  fi

  kind="$(fc_runtime_host_kind)"
  if [[ "$kind" == "vm_runtime" ]]; then
    return 0
  fi

  expected="$(fc_runtime_workspace_expected)"
  os="$(uname -s 2>/dev/null || printf 'unknown')"
  echo "[${caller}] VM-only execution policy: command refused on this host." >&2
  echo "[${caller}] detected_host_kind=${kind} os=${os} pwd=${PWD}" >&2
  echo "[${caller}] expected_workspace=${expected}" >&2
  echo "[${caller}] Set FC_ALLOW_LOCAL_MAC=1 only for exceptional debugging." >&2
  exit 3
}
