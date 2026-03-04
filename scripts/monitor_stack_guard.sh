#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
LOG_DIR="${FC_MONITOR_LOG_DIR:-$ROOT/logs-codex-runs}"
GUARD_LOG="${LOG_DIR}/monitor-guard.log"
LOCK_FILE="${FC_MONITOR_GUARD_LOCK_FILE:-/tmp/fc-monitor-guard.lock}"
LOCK_DIR_FALLBACK=""
LOCAL_URL="${FC_MONITOR_LOCAL_URL:-http://127.0.0.1:7779/api/status}"
LOCAL_DIAG_URL="${FC_MONITOR_LOCAL_DIAG_URL:-http://127.0.0.1:7779/api/runtime-diagnostics}"
PUBLIC_URL="${FC_MONITOR_PUBLIC_URL:-https://fc-monitor.loca.lt/api/status}"
PUBLIC_HEADER_KEY="${FC_MONITOR_PUBLIC_HEADER_KEY:-bypass-tunnel-reminder}"
PUBLIC_HEADER_VALUE="${FC_MONITOR_PUBLIC_HEADER_VALUE:-1}"
LT_SUBDOMAIN="${FC_MONITOR_LT_SUBDOMAIN:-fc-monitor}"
LT_HOST="${FC_MONITOR_LT_HOST:-https://loca.lt}"
LT_PORT="${FC_MONITOR_LT_PORT:-7779}"
if [[ "$ROOT" == /Users/* ]]; then
  MANAGE_TUNNEL="${FC_MONITOR_MANAGE_TUNNEL:-0}"
else
  MANAGE_TUNNEL="${FC_MONITOR_MANAGE_TUNNEL:-1}"
fi
if [[ "$ROOT" == /Users/* ]]; then
  # Host-side troubleshooting runs should not re-own the VM public tunnel.
  ENFORCE_PUBLIC_ROOT_MATCH="${FC_MONITOR_ENFORCE_PUBLIC_ROOT_MATCH:-0}"
else
  ENFORCE_PUBLIC_ROOT_MATCH="${FC_MONITOR_ENFORCE_PUBLIC_ROOT_MATCH:-1}"
fi
STALE_LOCK_MINUTES="${FC_MONITOR_GUARD_STALE_LOCK_MINUTES:-30}"

mkdir -p "$LOG_DIR"
cd "$ROOT"

ts() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

log() {
  printf '%s [monitor-guard] %s\n' "$(ts)" "$*" >> "$GUARD_LOG"
}

monitor_server_running() {
  pgrep -f 'scripts/monitor_server.py|apps/monitor/server.py|uvicorn.*7779' >/dev/null 2>&1 \
    || ss -ltn 2>/dev/null | awk '$4 ~ /:7779$/ {found=1} END{exit(found?0:1)}'
}

other_guard_running() {
  local pid=""
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    if [[ "$pid" != "$$" && "$pid" != "${PPID:-}" ]]; then
      return 0
    fi
  done < <(pgrep -f 'monitor_stack_guard.sh' 2>/dev/null || true)
  return 1
}

with_lock_or_exit() {
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
      exit 0
    fi
    return 0
  fi

  LOCK_DIR_FALLBACK="${LOCK_FILE}.dirlock"
  if ! mkdir "$LOCK_DIR_FALLBACK" 2>/dev/null; then
    if [[ -d "$LOCK_DIR_FALLBACK" ]] && { ! other_guard_running || find "$LOCK_DIR_FALLBACK" -maxdepth 0 -mmin "+${STALE_LOCK_MINUTES}" | grep -q .; }; then
      rmdir "$LOCK_DIR_FALLBACK" >/dev/null 2>&1 || true
      if ! mkdir "$LOCK_DIR_FALLBACK" 2>/dev/null; then
        exit 0
      fi
    else
      exit 0
    fi
  fi
  trap 'if [[ -n "${LOCK_DIR_FALLBACK:-}" ]]; then rmdir "$LOCK_DIR_FALLBACK" >/dev/null 2>&1 || true; fi' EXIT
}

is_local_up() {
  curl -fsS -m 5 -o /dev/null "$LOCAL_URL" >/dev/null 2>&1 \
    && curl -fsS -m 5 -o /dev/null "$LOCAL_DIAG_URL" >/dev/null 2>&1
}

is_public_up() {
  curl -fsS -m 8 -H "${PUBLIC_HEADER_KEY}: ${PUBLIC_HEADER_VALUE}" -o /dev/null "$PUBLIC_URL" >/dev/null 2>&1
}

public_queue_source() {
  curl -fsS -m 8 -H "${PUBLIC_HEADER_KEY}: ${PUBLIC_HEADER_VALUE}" "$PUBLIC_URL" 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(((d.get("sources") or {}).get("queue") or "").strip())' 2>/dev/null || true
}

public_matches_root() {
  local src=""
  src="$(public_queue_source)"
  [[ -n "$src" ]] && [[ "$src" == "$ROOT"* ]]
}

start_monitor_server() {
  (
    exec 9>&-
    nohup env FC_MONITOR_ROOT="$ROOT" python3 scripts/monitor_server.py >> "${LOG_DIR}/monitor-server.log" 2>&1 < /dev/null &
  )
  sleep 2
}

restart_monitor_server() {
  pkill -f 'scripts/monitor_server.py|apps/monitor/server.py' >/dev/null 2>&1 || true
  sleep 1
  start_monitor_server
}

start_tunnel() {
  local mode="${1:-host}"
  local -a cmd=(npx --yes localtunnel --port "${LT_PORT}" --subdomain "${LT_SUBDOMAIN}" --local-host 127.0.0.1)
  if [[ "$mode" == "host" && -n "$LT_HOST" ]]; then
    cmd+=(--host "$LT_HOST")
  fi
  (
    exec 9>&-
    nohup "${cmd[@]}" >> "${LOG_DIR}/monitor-tunnel.log" 2>&1 < /dev/null &
  )
  sleep 3
}

tunnel_pid_list() {
  local leaf=""
  leaf="$(ps -eo pid=,args= 2>/dev/null | awk -v domain="$LT_SUBDOMAIN" -v port="$LT_PORT" '
    {
      pid=$1
      $1=""
      line=substr($0,2)
      if (line ~ /monitor_stack_guard\.sh/) next
      if (line !~ /\/bin\/lt([[:space:]]|$)/) next
      if (line !~ ("--subdomain[ =]" domain)) next
      if (line !~ ("--port[ =]" port)) next
      print pid
    }
  ')"
  if [[ -n "$leaf" ]]; then
    printf '%s\n' "$leaf"
    return 0
  fi
  ps -eo pid=,args= 2>/dev/null | awk -v domain="$LT_SUBDOMAIN" -v port="$LT_PORT" '
    {
      pid=$1
      $1=""
      line=substr($0,2)
      if (line ~ /monitor_stack_guard\.sh/) next
      if (line !~ /(localtunnel|\/lt([[:space:]]|$))/) next
      if (line !~ ("--subdomain[ =]" domain)) next
      if (line !~ ("--port[ =]" port)) next
      print pid
    }
  '
}

tunnel_process_count() {
  local count=0
  while IFS= read -r _pid; do
    ((count+=1))
  done < <(tunnel_pid_list)
  printf '%s\n' "$count"
}

tunnel_process_running() {
  [[ "$(tunnel_process_count)" -gt 0 ]]
}

stop_tunnel() {
  local pid=""
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    kill "$pid" >/dev/null 2>&1 || true
  done < <(tunnel_pid_list)
  sleep 1
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  done < <(tunnel_pid_list)
}

restart_tunnel() {
  stop_tunnel
  local mode=""
  for mode in host plain; do
    log "restart tunnel mode=${mode}"
    start_tunnel "$mode"
    if tunnel_process_running && is_public_up; then
      log "tunnel healthy mode=${mode}"
      return 0
    fi
    stop_tunnel
  done
  return 1
}

with_lock_or_exit

initial_local_up=0
if is_local_up; then
  initial_local_up=1
fi

if ! monitor_server_running; then
  if [[ "$initial_local_up" -eq 1 ]]; then
    log "monitor process not detected but local api already up; skip forced restart"
  else
    log "monitor_server missing and local api down; starting"
    start_monitor_server
  fi
fi

if ! is_local_up; then
  log "local api down; restarting monitor server"
  restart_monitor_server
fi

if ! is_local_up; then
  log "error local api unavailable after restart attempt"
  exit 1
fi

if [[ "$MANAGE_TUNNEL" == "1" ]]; then
  tc="$(tunnel_process_count)"
  if [[ "$tc" -gt 1 ]]; then
    log "duplicate tunnel processes detected count=${tc}; restarting"
    restart_tunnel || true
  fi

  if ! tunnel_process_running; then
    log "tunnel process missing; starting"
    start_tunnel host
  fi

  if ! is_public_up; then
    log "public tunnel unavailable; restarting tunnel"
    restart_tunnel || true
  fi

  if [[ "$ENFORCE_PUBLIC_ROOT_MATCH" == "1" ]] && is_public_up && ! public_matches_root; then
    log "public root mismatch (expected_root=${ROOT}); restarting tunnel"
    restart_tunnel || true
  fi

  if is_local_up && is_public_up && { [[ "$ENFORCE_PUBLIC_ROOT_MATCH" != "1" ]] || public_matches_root; }; then
    log "ok local=up public=up"
  else
    log "error local/public not healthy after restart attempt"
    exit 1
  fi
else
  log "ok local=up public=skip"
fi
