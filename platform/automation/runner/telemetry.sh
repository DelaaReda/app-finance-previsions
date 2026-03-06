#!/usr/bin/env bash

runner_append_trace() {
  local trace_file="${1:-}"
  shift || true
  local line="$*"
  [[ -n "$trace_file" ]] || return 0
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$line" >> "$trace_file"
}

runner_emit_telemetry_jsonl() {
  local file="$1"
  local event="$2"
  local role="${3:-unknown}"
  shift 3 || true
  mkdir -p "$(dirname "$file")"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local fields=""
  local kv=""
  for kv in "$@"; do
    [[ -n "$kv" ]] || continue
    local k="${kv%%=*}"
    local v="${kv#*=}"
    fields="${fields},\"${k}\":\"${v}\""
  done
  printf '{"ts_utc":"%s","event":"%s","role":"%s"%s}\n' "$ts" "$event" "$role" "$fields" >> "$file"
}
