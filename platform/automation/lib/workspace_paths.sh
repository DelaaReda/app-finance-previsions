#!/usr/bin/env bash

# Shared workspace path resolution for runtime/orchestration scripts.
# Single source of truth to avoid divergent ROOT logic across scripts.

fc_workspace_has_layout() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  [[ -d "$candidate/scripts" ]] && [[ -d "$candidate/platform" ]]
}

fc_workspace_writable() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  mkdir -p "$candidate/logs-codex-runs" >/dev/null 2>&1 || return 1
  [[ -w "$candidate/logs-codex-runs" ]]
}

fc_resolve_workspace_root() {
  local script_dir="${1:-}"
  local -a candidates=()
  local candidate=""
  local parent=""
  local grandparent=""

  if [[ -n "${FC_WORKSPACE_ROOT:-}" ]]; then
    candidates+=("${FC_WORKSPACE_ROOT}")
  fi

  if [[ -n "${HOME:-}" ]]; then
    candidates+=(
      "${HOME}/Documents/analyse-financiere"
      "${HOME}/analyse-financiere"
    )
  fi

  candidates+=(
    "/home/venom/analyse-financiere"
    "/home/venom/shared/analyse-financiere"
  )

  if [[ -n "$script_dir" ]]; then
    parent="$(cd "${script_dir}/.." && pwd -P 2>/dev/null || true)"
    grandparent="$(cd "${script_dir}/../.." && pwd -P 2>/dev/null || true)"
    [[ -n "$parent" ]] && candidates+=("$parent")
    [[ -n "$grandparent" ]] && candidates+=("$grandparent")
  fi

  for candidate in "${candidates[@]}"; do
    if fc_workspace_has_layout "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if [[ -n "$parent" ]]; then
    printf '%s\n' "$parent"
    return 0
  fi
  printf '%s\n' "${script_dir:-.}"
}

fc_prefer_writable_workspace() {
  local root="${1:-}"
  local fallback=""
  if fc_workspace_writable "$root"; then
    printf '%s\n' "$root"
    return 0
  fi

  # When launched from the shared mount, prefer the VM canonical workspace if it is writable.
  # This avoids split runtime state between /home/venom/analyse-financiere and /home/venom/shared/analyse-financiere.
  if [[ "${PWD:-}" == "/home/venom/shared/analyse-financiere"* ]] \
    && fc_workspace_has_layout "/home/venom/analyse-financiere" \
    && fc_workspace_writable "/home/venom/analyse-financiere"; then
    printf '%s\n' "/home/venom/analyse-financiere"
    return 0
  fi

  # Prefer current working directory when it already is a valid writable workspace.
  if [[ -n "${PWD:-}" ]] \
    && fc_workspace_has_layout "$PWD" \
    && fc_workspace_writable "$PWD"; then
    printf '%s\n' "$PWD"
    return 0
  fi

  if [[ -n "${HOME:-}" ]]; then
    for fallback in "${HOME}/Documents/analyse-financiere" "${HOME}/analyse-financiere"; do
      if [[ "$fallback" == "$root" ]]; then
        continue
      fi
      if fc_workspace_has_layout "$fallback" && fc_workspace_writable "$fallback"; then
        printf '%s\n' "$fallback"
        return 0
      fi
    done
  fi

  # VM canonical first, shared mount second (shared can be read-only in incidents).
  for fallback in "/home/venom/analyse-financiere" "/home/venom/shared/analyse-financiere"; do
    if [[ "$fallback" == "$root" ]]; then
      continue
    fi
    if fc_workspace_has_layout "$fallback" && fc_workspace_writable "$fallback"; then
      printf '%s\n' "$fallback"
      return 0
    fi
  done

  printf '%s\n' "$root"
}
