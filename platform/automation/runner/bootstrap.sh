#!/usr/bin/env bash

runner_resolve_helper_script() {
  local root="${1:-}"
  local primary="${2:-}"
  local fallback="${3:-}"
  [[ -n "$root" ]] || return 2
  [[ -n "$primary" ]] || return 2
  if [[ -f "$root/$primary" ]]; then
    printf '%s\n' "$root/$primary"
    return 0
  fi
  if [[ -n "$fallback" && -f "$root/$fallback" ]]; then
    printf '%s\n' "$root/$fallback"
    return 0
  fi
  printf '%s\n' "$root/$primary"
  return 0
}

runner_mkdir_required() {
  local p
  for p in "$@"; do
    [[ -n "$p" ]] || continue
    mkdir -p "$p"
  done
}
