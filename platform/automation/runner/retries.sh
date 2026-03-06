#!/usr/bin/env bash

runner_normalize_seconds() {
  local raw="${1:-}"
  local fallback="${2:-60}"
  local min="${3:-1}"
  local max="${4:-3600}"
  if ! [[ "$raw" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$fallback"
    return 0
  fi
  if (( raw < min )); then
    printf '%s\n' "$fallback"
    return 0
  fi
  if (( raw > max )); then
    printf '%s\n' "$max"
    return 0
  fi
  printf '%s\n' "$raw"
}

runner_retry_backoff_seconds() {
  local attempt="${1:-1}"
  local base="${2:-5}"
  local cap="${3:-120}"
  local expo=$(( base * (2 ** (attempt - 1)) ))
  if (( expo > cap )); then
    expo="$cap"
  fi
  printf '%s\n' "$expo"
}
