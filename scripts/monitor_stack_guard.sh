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
LOCK_FILE="${FC_MONITOR_GUARD_LOCK_FILE:-/tmp/fc-monitor-guard.v2.lock}"
LOCK_DIR_FALLBACK=""
LOCAL_URL="${FC_MONITOR_LOCAL_URL:-http://127.0.0.1:7779/api/status}"
LOCAL_DIAG_URL="${FC_MONITOR_LOCAL_DIAG_URL:-http://127.0.0.1:7779/api/runtime-diagnostics}"
PUBLIC_URL="${FC_MONITOR_PUBLIC_URL:-https://fc-monitor.loca.lt/api/status}"
PUBLIC_HEADER_KEY="${FC_MONITOR_PUBLIC_HEADER_KEY:-bypass-tunnel-reminder}"
PUBLIC_HEADER_VALUE="${FC_MONITOR_PUBLIC_HEADER_VALUE:-1}"
PUBLIC_URL_STATE_FILE="${FC_MONITOR_PUBLIC_URL_STATE_FILE:-${LOG_DIR}/monitor-public-url.txt}"
PUBLIC_FAILURE_STATE_FILE="${FC_MONITOR_PUBLIC_FAILURE_STATE_FILE:-${LOG_DIR}/monitor-public-fail-streak.txt}"
PUBLIC_FAILURE_THRESHOLD="${FC_MONITOR_PUBLIC_FAILURE_THRESHOLD:-2}"
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
if [[ "$ROOT" == /Users/* ]]; then
  FC_MONITOR_AUTO_START_STACK="${FC_MONITOR_AUTO_START_STACK:-0}"
else
  FC_MONITOR_AUTO_START_STACK="${FC_MONITOR_AUTO_START_STACK:-1}"
fi
FC_MONITOR_AUTO_START_COOLDOWN_SECONDS="${FC_MONITOR_AUTO_START_COOLDOWN_SECONDS:-600}"
AUTO_START_STATE_FILE="${FC_MONITOR_AUTO_START_STATE_FILE:-${LOG_DIR}/monitor-auto-start.last}"
STALE_LOCK_MINUTES="${FC_MONITOR_GUARD_STALE_LOCK_MINUTES:-30}"

mkdir -p "$LOG_DIR"
cd "$ROOT"

ts() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

log() {
  printf '%s [monitor-guard] %s\n' "$(ts)" "$*" >> "$GUARD_LOG"
}

current_public_url() {
  local from_state=""
  if [[ -f "$PUBLIC_URL_STATE_FILE" ]]; then
    from_state="$(head -n 1 "$PUBLIC_URL_STATE_FILE" 2>/dev/null | tr -d '\r' | sed 's/^ *//; s/ *$//')"
  fi
  if [[ -n "$from_state" ]]; then
    printf '%s\n' "$from_state"
    return 0
  fi
  printf '%s\n' "$PUBLIC_URL"
}

write_public_url_state() {
  local url="${1:-}"
  [[ -n "$url" ]] || return 0
  printf '%s\n' "$url" > "$PUBLIC_URL_STATE_FILE"
}

read_public_fail_streak() {
  if [[ -f "$PUBLIC_FAILURE_STATE_FILE" ]]; then
    local n=""
    n="$(head -n 1 "$PUBLIC_FAILURE_STATE_FILE" 2>/dev/null | tr -d '\r' | sed 's/^ *//; s/ *$//')"
    if [[ "$n" =~ ^[0-9]+$ ]]; then
      printf '%s\n' "$n"
      return 0
    fi
  fi
  printf '0\n'
}

write_public_fail_streak() {
  local n="${1:-0}"
  if ! [[ "$n" =~ ^[0-9]+$ ]]; then
    n=0
  fi
  printf '%s\n' "$n" > "$PUBLIC_FAILURE_STATE_FILE"
}

read_auto_start_epoch() {
  if [[ -f "$AUTO_START_STATE_FILE" ]]; then
    local n=""
    n="$(head -n 1 "$AUTO_START_STATE_FILE" 2>/dev/null | tr -d '\r' | sed 's/^ *//; s/ *$//')"
    if [[ "$n" =~ ^[0-9]+$ ]]; then
      printf '%s\n' "$n"
      return 0
    fi
  fi
  printf '0\n'
}

write_auto_start_epoch() {
  local n="${1:-0}"
  if ! [[ "$n" =~ ^[0-9]+$ ]]; then
    n=0
  fi
  printf '%s\n' "$n" > "$AUTO_START_STATE_FILE"
}

monitor_server_running() {
  pgrep -f 'scripts/monitor_server.py|apps/monitor/server.py|uvicorn.*7779' >/dev/null 2>&1 \
    || ss -ltn 2>/dev/null | awk '$4 ~ /:7779$/ {found=1} END{exit(found?0:1)}'
}

stack_process_running() {
  pgrep -f 'python.*run_api.py|uvicorn.*8050|http.server 5173|vite.*5173|scripts/monitor_server.py|apps/monitor/server.py' >/dev/null 2>&1
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
  # Keep local liveness check lightweight and stable: `/api/runtime-diagnostics`
  # can be heavier and should not trigger monitor restarts when `/api/status` is up.
  curl -fsS -m 5 -o /dev/null "$LOCAL_URL" >/dev/null 2>&1
}

is_public_up() {
  local url=""
  url="$(current_public_url)"
  curl -fsS -m 8 -H "${PUBLIC_HEADER_KEY}: ${PUBLIC_HEADER_VALUE}" -o /dev/null "$url" >/dev/null 2>&1
}

public_queue_source() {
  local url=""
  url="$(current_public_url)"
  curl -fsS -m 8 -H "${PUBLIC_HEADER_KEY}: ${PUBLIC_HEADER_VALUE}" "$url" 2>/dev/null \
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

auto_start_stack_if_needed() {
  if [[ "$FC_MONITOR_AUTO_START_STACK" != "1" ]]; then
    return 0
  fi
  if is_local_up; then
    return 0
  fi
  if stack_process_running; then
    return 0
  fi
  if ! [[ "$FC_MONITOR_AUTO_START_COOLDOWN_SECONDS" =~ ^[0-9]+$ ]] || [[ "$FC_MONITOR_AUTO_START_COOLDOWN_SECONDS" -lt 60 ]]; then
    FC_MONITOR_AUTO_START_COOLDOWN_SECONDS=600
  fi

  local now last elapsed
  now="$(date +%s)"
  last="$(read_auto_start_epoch)"
  elapsed=$((now - last))
  if [[ "$last" -gt 0 && "$elapsed" -lt "$FC_MONITOR_AUTO_START_COOLDOWN_SECONDS" ]]; then
    log "auto_start_stack cooldown active elapsed=${elapsed}s threshold=${FC_MONITOR_AUTO_START_COOLDOWN_SECONDS}s"
    return 0
  fi

  local exec_safe="$ROOT/platform/policies/exec_safe.sh"
  local output="" rc=0
  if [[ ! -x "$exec_safe" ]]; then
    log "auto_start_stack skipped: exec_safe missing at $exec_safe"
    return 0
  fi

  set +e
  # Prevent lock-fd inheritance into long-lived children (run_api/monitor),
  # otherwise future guard runs may permanently fail to acquire the lock.
  output="$( (exec 9>&-; "$exec_safe" --workdir "$ROOT" -- "./finance-copilot.sh start") 2>&1 )"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    write_auto_start_epoch "$now"
    log "auto_start_stack success cooldown=${FC_MONITOR_AUTO_START_COOLDOWN_SECONDS}s detail=$(printf '%s' "$output" | tail -n 1 | tr -s ' ' | cut -c1-180)"
  else
    log "auto_start_stack failed rc=${rc} detail=$(printf '%s' "$output" | tail -n 2 | tr '\n' ' ' | tr -s ' ' | cut -c1-220)"
  fi
}

start_tunnel() {
  local mode="${1:-host}"
  local -a cmd=(npx --yes localtunnel --port "${LT_PORT}" --local-host 127.0.0.1)
  if [[ "$mode" == "host" ]]; then
    cmd+=(--subdomain "${LT_SUBDOMAIN}")
  fi
  if [[ "$mode" == "host" && -n "$LT_HOST" ]]; then
    cmd+=(--host "$LT_HOST")
  fi

  local before_lines=0
  if [[ -f "${LOG_DIR}/monitor-tunnel.log" ]]; then
    before_lines="$(wc -l < "${LOG_DIR}/monitor-tunnel.log" 2>/dev/null || echo 0)"
    if ! [[ "$before_lines" =~ ^[0-9]+$ ]]; then
      before_lines=0
    fi
  fi

  (
    exec 9>&-
    nohup "${cmd[@]}" >> "${LOG_DIR}/monitor-tunnel.log" 2>&1 < /dev/null &
  )
  sleep 4

  local discovered_url=""
  local from_new=""
  from_new="$(tail -n +"$((before_lines + 1))" "${LOG_DIR}/monitor-tunnel.log" 2>/dev/null | rg -o 'https://[a-z0-9-]+\.loca\.lt' | tail -n 1 || true)"
  if [[ -n "$from_new" ]]; then
    discovered_url="$from_new"
  else
    discovered_url="$(tail -n 40 "${LOG_DIR}/monitor-tunnel.log" 2>/dev/null | rg -o 'https://[a-z0-9-]+\.loca\.lt' | tail -n 1 || true)"
  fi

  if [[ "$mode" == "host" ]]; then
    write_public_url_state "$PUBLIC_URL"
  fi
  if [[ -n "$discovered_url" ]]; then
    if [[ "$mode" != "host" || "$discovered_url" == *"${LT_SUBDOMAIN}.loca.lt" ]]; then
      write_public_url_state "${discovered_url}/api/status"
    fi
    log "tunnel url discovered mode=${mode} url=${discovered_url}"
  fi
}

tunnel_pid_list() {
  local leaf=""
  leaf="$(ps -eo pid=,args= 2>/dev/null | awk -v port="$LT_PORT" '
    {
      pid=$1
      $1=""
      line=substr($0,2)
      if (line ~ /monitor_stack_guard\.sh/) next
      if (line !~ /\/bin\/lt([[:space:]]|$)/) next
      if (line !~ ("--port[ =]" port)) next
      print pid
    }
  ')"
  if [[ -n "$leaf" ]]; then
    printf '%s\n' "$leaf"
    return 0
  fi
  ps -eo pid=,args= 2>/dev/null | awk -v port="$LT_PORT" '
    {
      pid=$1
      $1=""
      line=substr($0,2)
      if (line ~ /monitor_stack_guard\.sh/) next
      if (line !~ /(localtunnel|\/lt([[:space:]]|$))/) next
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
      log "tunnel healthy mode=${mode} url=$(current_public_url)"
      write_public_fail_streak 0
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

if [[ "$initial_local_up" -eq 0 ]]; then
  auto_start_stack_if_needed
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
  if ! [[ "$PUBLIC_FAILURE_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$PUBLIC_FAILURE_THRESHOLD" -lt 1 ]]; then
    PUBLIC_FAILURE_THRESHOLD=2
  fi
  tc="$(tunnel_process_count)"
  if [[ "$tc" -gt 1 ]]; then
    log "duplicate tunnel processes detected count=${tc}; restarting"
    restart_tunnel || true
  fi

  if ! tunnel_process_running; then
    log "tunnel process missing; starting"
    start_tunnel host
  fi

  if is_public_up; then
    write_public_fail_streak 0
  else
    # Retry once before counting a failure to reduce transient public 503 windows.
    sleep 2
    if is_public_up; then
      write_public_fail_streak 0
    else
      fail_streak="$(read_public_fail_streak)"
      fail_streak="$((fail_streak + 1))"
      write_public_fail_streak "$fail_streak"
      if [[ "$fail_streak" -ge "$PUBLIC_FAILURE_THRESHOLD" ]]; then
        log "public tunnel unavailable streak=${fail_streak}; restarting tunnel"
        restart_tunnel || true
        if is_public_up; then
          write_public_fail_streak 0
        fi
      else
        log "public tunnel unavailable streak=${fail_streak}/${PUBLIC_FAILURE_THRESHOLD}; defer restart"
      fi
    fi
  fi

  if [[ "$ENFORCE_PUBLIC_ROOT_MATCH" == "1" ]] && is_public_up && ! public_matches_root; then
    log "public root mismatch (expected_root=${ROOT}); restarting tunnel"
    restart_tunnel || true
  fi

  if is_local_up && is_public_up && { [[ "$ENFORCE_PUBLIC_ROOT_MATCH" != "1" ]] || public_matches_root; }; then
    log "ok local=up public=up url=$(current_public_url)"
  else
    log "warn local/public degraded local=$(is_local_up && echo up || echo down) public=$(is_public_up && echo up || echo down) url=$(current_public_url)"
    exit 0
  fi
else
  log "ok local=up public=skip"
fi
