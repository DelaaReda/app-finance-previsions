#!/usr/bin/env bash

# Shared workspace path resolution for runtime/orchestration scripts.
# Single source of truth to avoid divergent ROOT logic across scripts.

fc_normalize_workspace_candidate() {
  local candidate="${1:-}"
  local canonical_root="/home/venom/analyse-financiere"
  local shared_root="/home/venom/shared/analyse-financiere"
  local suffix=""

  [[ -n "$candidate" ]] || return 1

  if [[ "$candidate" == "$shared_root" ]] || [[ "$candidate" == "$shared_root/"* ]]; then
    if [[ -d "$canonical_root" ]]; then
      suffix="${candidate#"$shared_root"}"
      printf '%s%s\n' "$canonical_root" "$suffix"
      return 0
    fi
  fi

  printf '%s\n' "$candidate"
}

fc_workspace_realpath() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  (
    cd "$candidate" >/dev/null 2>&1 || exit 1
    pwd -P
  )
}

fc_workspace_samefile() {
  local left="${1:-}"
  local right="${2:-}"
  local left_real=""
  local right_real=""

  [[ -n "$left" && -n "$right" ]] || return 1
  left_real="$(fc_workspace_realpath "$left" 2>/dev/null || true)"
  right_real="$(fc_workspace_realpath "$right" 2>/dev/null || true)"
  [[ -n "$left_real" && -n "$right_real" && "$left_real" == "$right_real" ]]
}

fc_proc_cwd() {
  local pid="${1:-}"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  readlink "/proc/${pid}/cwd" 2>/dev/null
}

fc_workspace_runtime_path_invalid() {
  local candidate="${1:-}"
  local root="${2:-}"
  [[ -n "$candidate" && -n "$root" ]] || return 0
  candidate="$(fc_normalize_workspace_candidate "$candidate")"
  root="$(fc_normalize_workspace_candidate "$root")"
  [[ "$candidate" == *"(deleted)"* ]] && return 0
  case "$candidate" in
    "$root"|"$root"/*)
      return 1
      ;;
  esac
  return 0
}

fc_pid_workspace_invalid() {
  local pid="${1:-}"
  local root="${2:-}"
  local cwd=""
  [[ "$pid" =~ ^[0-9]+$ && -n "$root" ]] || return 0
  cwd="$(fc_proc_cwd "$pid" 2>/dev/null || true)"
  fc_workspace_runtime_path_invalid "$cwd" "$root"
}

fc_workspace_has_layout() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  candidate="$(fc_normalize_workspace_candidate "$candidate")"
  [[ -d "$candidate/scripts" ]] && [[ -d "$candidate/platform" ]]
}

fc_workspace_writable() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  candidate="$(fc_normalize_workspace_candidate "$candidate")"
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
  )

  if [[ -n "$script_dir" ]]; then
    parent="$(cd "${script_dir}/.." && pwd -P 2>/dev/null || true)"
    grandparent="$(cd "${script_dir}/../.." && pwd -P 2>/dev/null || true)"
    [[ -n "$parent" ]] && candidates+=("$parent")
    [[ -n "$grandparent" ]] && candidates+=("$grandparent")
  fi

  for candidate in "${candidates[@]}"; do
    candidate="$(fc_normalize_workspace_candidate "$candidate")"
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
  root="$(fc_normalize_workspace_candidate "$root")"
  if fc_workspace_writable "$root"; then
    printf '%s\n' "$root"
    return 0
  fi

  # Always prefer the VM canonical workspace when it is available and writable.
  # The shared alias is compatibility-only and must not become the execution root.
  if [[ "$root" != "/home/venom/analyse-financiere" ]] \
    && fc_workspace_has_layout "/home/venom/analyse-financiere" \
    && fc_workspace_writable "/home/venom/analyse-financiere"; then
    printf '%s\n' "/home/venom/analyse-financiere"
    return 0
  fi

  # Prefer current working directory when it already is a valid writable workspace.
  if [[ -n "${PWD:-}" ]] \
    && fc_workspace_has_layout "$(fc_normalize_workspace_candidate "$PWD")" \
    && fc_workspace_writable "$(fc_normalize_workspace_candidate "$PWD")"; then
    printf '%s\n' "$(fc_normalize_workspace_candidate "$PWD")"
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

  # VM canonical only; shared alias remains compatibility-only.
  for fallback in "/home/venom/analyse-financiere"; do
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
