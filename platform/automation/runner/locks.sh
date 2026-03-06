#!/usr/bin/env bash

runner_lock_age_seconds() {
  local lock_meta="$1"
  [[ -f "$lock_meta" ]] || { printf '0\n'; return 0; }
  local start_epoch
  start_epoch="$(sed -n 's/.*start_epoch=\([0-9][0-9]*\).*/\1/p' "$lock_meta" | head -n 1)"
  if ! [[ "$start_epoch" =~ ^[0-9]+$ ]]; then
    printf '0\n'
    return 0
  fi
  local now
  now="$(date +%s)"
  local age=$(( now - start_epoch ))
  if (( age < 0 )); then
    age=0
  fi
  printf '%s\n' "$age"
}

runner_lock_is_stale() {
  local lock_meta="$1"
  local ttl="${2:-900}"
  local age
  age="$(runner_lock_age_seconds "$lock_meta")"
  (( age > ttl ))
}

runner_lock_holder_pid() {
  local lock_meta="$1"
  [[ -f "$lock_meta" ]] || { printf '\n'; return 0; }
  sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' "$lock_meta" | head -n 1
}

runner_lock_holder_alive() {
  local lock_meta="$1"
  local pid
  pid="$(runner_lock_holder_pid "$lock_meta")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

runner_lock_stale_without_holder() {
  local lock_meta="$1"
  local ttl="${2:-900}"
  runner_lock_is_stale "$lock_meta" "$ttl" && ! runner_lock_holder_alive "$lock_meta"
}

runner_lock_write_meta() {
  local lock_meta="$1"
  local role="${2:-unknown}"
  local tick_id="${3:-unknown}"
  local layer="${4:-run}"
  local lock_file="${5:-unknown}"
  local ts now
  now="$(date +%s)"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'pid=%s host=%s start_epoch=%s start_utc=%s role=%s layer=%s tick_id=%s lock_file=%s\n' \
    "$$" "${HOSTNAME:-unknown}" "$now" "$ts" "$role" "$layer" "$tick_id" "$lock_file" > "$lock_meta"
}
