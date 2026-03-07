#!/usr/bin/env bash
# cleanup_stale_role_locks.sh — TRILOCK cleanup (tick/run/memory), safe + idempotent.
set -uo pipefail

STATE_DIR="${FC_ROLE_STATE_DIR:-${TMUX_ROLE_STATE_DIR:-${HOME}/.openclaw/cron/role-state}}"
RUNTIME_LOCK_DIR="${FC_RUNTIME_LOCK_DIR:-/tmp/fc-agent-locks}"
STALE_MIN="${FC_STALE_LOCK_MINUTES:-15}"
LOG="${FC_STALE_LOCK_LOG:-/tmp/fc-stale-lock-cleanup.log}"
TRILOCK_ORDER="tick>run>memory"

if ! [[ "$STALE_MIN" =~ ^[0-9]+$ ]] || [[ "$STALE_MIN" -lt 1 ]]; then
  STALE_MIN=15
fi
STALE_SECONDS=$(( STALE_MIN * 60 ))

ts() { date '+%Y-%m-%dT%H:%M:%S'; }

stat_mtime() {
  local file="$1"
  stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo 0
}

file_age_seconds() {
  local file="$1"
  local mtime now
  mtime="$(stat_mtime "$file")"
  if ! [[ "$mtime" =~ ^[0-9]+$ ]]; then
    echo 0
    return 0
  fi
  now="$(date +%s)"
  if [[ "$now" -lt "$mtime" ]]; then
    echo 0
    return 0
  fi
  echo $(( now - mtime ))
}

read_meta_field() {
  local key="$1"
  local meta="$2"
  [[ -f "$meta" ]] || return 1
  sed -n "s/.*${key}=\\([^[:space:]]*\\).*/\\1/p" "$meta" | head -n 1
}

is_pid_alive() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

is_open_by_fd() {
  local file="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof "$file" >/dev/null 2>&1
    return $?
  fi
  return 1
}

list_holder_commands() {
  local file="$1"
  command -v lsof >/dev/null 2>&1 || return 0
  lsof "$file" 2>/dev/null | awk 'NR>1 {print $1 ":" $2}' | sort -u
}

role_runtime_process_alive() {
  local role="$1"
  pgrep -af "fc_agent_tick\\.sh[[:space:]]+${role}($|[[:space:]])|cron_tmux_role_runner\\.sh[[:space:]]+${role}($|[[:space:]])" >/dev/null 2>&1
}

tmux_session_for_role() {
  local role="$1"
  case "$role" in
    clawsentinel) printf '%s\n' "clawsentinel" ;;
    *) printf '%s\n' "codex_${role}_cron" ;;
  esac
}

log_event() {
  local kind="$1"
  local layer="$2"
  local lock_path="$3"
  local role="$4"
  local age_s="$5"
  local owner_pid="$6"
  local owner_host="$7"
  local reason="$8"
  printf '%s [%s] layer=%s role=%s age_s=%s owner_pid=%s owner_host=%s lock=%s order=%s reason=%s\n' \
    "$(ts)" "$kind" "$layer" "$role" "$age_s" "${owner_pid:-unknown}" "${owner_host:-unknown}" "$lock_path" "$TRILOCK_ORDER" "$reason" >> "$LOG"
}

role_from_lock_path() {
  local lock_path="$1"
  local base
  base="$(basename "$lock_path")"
  base="${base%%.run.lock}"
  base="${base%%.memory.lock}"
  base="${base%%.lock}"
  base="${base%%.lock.dirlock}"
  printf '%s\n' "$base"
}

scanned=0
cleaned=0
skipped_active=0
skipped_fresh=0

process_lock_file() {
  local layer="$1"
  local lock_path="$2"
  local meta_path="${lock_path}.meta"
  local role owner_pid owner_host start_epoch age_s holder_cmds session
  local reason=""

  [[ -f "$lock_path" ]] || return 0
  scanned=$((scanned + 1))
  role="$(role_from_lock_path "$lock_path")"
  age_s="$(file_age_seconds "$lock_path")"
  owner_pid="$(read_meta_field "pid" "$meta_path" || true)"
  owner_host="$(read_meta_field "host" "$meta_path" || true)"
  start_epoch="$(read_meta_field "start_epoch" "$meta_path" || true)"
  if [[ "$start_epoch" =~ ^[0-9]+$ ]]; then
    now_epoch="$(date +%s)"
    if [[ "$now_epoch" -ge "$start_epoch" ]]; then
      age_s=$(( now_epoch - start_epoch ))
    fi
  fi

  if [[ "$age_s" -lt "$STALE_SECONDS" ]]; then
    skipped_fresh=$((skipped_fresh + 1))
    return 0
  fi

  if is_pid_alive "$owner_pid"; then
    skipped_active=$((skipped_active + 1))
    log_event "SKIP_ACTIVE" "$layer" "$lock_path" "$role" "$age_s" "$owner_pid" "$owner_host" "pid_alive"
    return 0
  fi

  if is_open_by_fd "$lock_path"; then
    holder_cmds="$(list_holder_commands "$lock_path" | tr '\n' ' ' | sed 's/  */ /g' | cut -c1-220)"
    if [[ "$layer" == "tick" && ! -f "$meta_path" && "$holder_cmds" == *"tmux:"* ]] && ! role_runtime_process_alive "$role"; then
      session="$(tmux_session_for_role "$role")"
      if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$session" 2>/dev/null; then
        tmux kill-session -t "$session" >/dev/null 2>&1 || true
      fi
      rm -f "$lock_path" "$meta_path" 2>/dev/null || true
      cleaned=$((cleaned + 1))
      log_event "CLEANED" "$layer" "$lock_path" "$role" "$age_s" "$owner_pid" "$owner_host" "tmux_inherited_fd_cleanup"
      return 0
    fi
    skipped_active=$((skipped_active + 1))
    log_event "SKIP_ACTIVE" "$layer" "$lock_path" "$role" "$age_s" "$owner_pid" "$owner_host" "open_fd${holder_cmds:+:$holder_cmds}"
    return 0
  fi

  rm -f "$lock_path" "$meta_path" 2>/dev/null || true
  cleaned=$((cleaned + 1))
  reason="stale_cleanup"
  log_event "CLEANED" "$layer" "$lock_path" "$role" "$age_s" "$owner_pid" "$owner_host" "$reason"
}

process_lock_dir() {
  local layer="$1"
  local lock_dir="$2"
  local role age_s

  [[ -d "$lock_dir" ]] || return 0
  scanned=$((scanned + 1))
  role="$(role_from_lock_path "$lock_dir")"
  age_s="$(file_age_seconds "$lock_dir")"
  if [[ "$age_s" -lt "$STALE_SECONDS" ]]; then
    skipped_fresh=$((skipped_fresh + 1))
    return 0
  fi
  rmdir "$lock_dir" >/dev/null 2>&1 || true
  rm -f "${lock_dir}.meta" >/dev/null 2>&1 || true
  cleaned=$((cleaned + 1))
  log_event "CLEANED" "$layer" "$lock_dir" "$role" "$age_s" "unknown" "unknown" "stale_dirlock_cleanup"
}

shopt -s nullglob

for f in "$RUNTIME_LOCK_DIR"/*.lock; do
  process_lock_file "tick" "$f"
done
for d in "$RUNTIME_LOCK_DIR"/*.lock.dirlock; do
  process_lock_dir "tick" "$d"
done
for f in "$STATE_DIR"/*.run.lock; do
  process_lock_file "run" "$f"
done
for f in "$STATE_DIR"/*.memory.lock; do
  process_lock_file "memory" "$f"
done

# Explicit legacy path handling for scrum_master lock files that may live
# directly under STATE_DIR (outside *.run.lock pattern).
if [[ -f "$STATE_DIR/scrum_master.lock" ]]; then
  process_lock_file "run" "$STATE_DIR/scrum_master.lock"
fi
if [[ -d "$STATE_DIR/scrum_master.lock.dirlock" ]]; then
  process_lock_dir "tick" "$STATE_DIR/scrum_master.lock.dirlock"
fi

shopt -u nullglob

printf '%s [DONE] scanned=%d cleaned=%d skipped_active=%d skipped_fresh=%d stale_min=%d\n' \
  "$(ts)" "$scanned" "$cleaned" "$skipped_active" "$skipped_fresh" "$STALE_MIN" >> "$LOG"
