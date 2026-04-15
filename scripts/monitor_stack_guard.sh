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
MONITOR_APP_SCRIPT="${FC_MONITOR_APP_SCRIPT:-$ROOT/apps/monitor/server.py}"
MONITOR_PYTHON_BIN="${FC_MONITOR_PYTHON_BIN:-$ROOT/apps/monitor/.venv/bin/python}"
MONITOR_LAN_PROXY_SCRIPT="${FC_MONITOR_LAN_PROXY_SCRIPT:-$ROOT/scripts/monitor_lan_proxy.py}"
BACKEND_HEAL_SCRIPT="${FC_BACKEND_HEAL_SCRIPT:-$ROOT/scripts/restart_api_if_stale.sh}"
LOCAL_URL="${FC_MONITOR_LOCAL_URL:-http://127.0.0.1:7779/api/monitor/access}"
LOCAL_DIAG_URL="${FC_MONITOR_LOCAL_DIAG_URL:-http://127.0.0.1:7779/api/runtime-diagnostics}"
LAN_PROXY_HOST="${FC_MONITOR_LAN_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
LAN_PROXY_PORT="${FC_MONITOR_LAN_PORT:-7780}"
LAN_PROXY_TARGET_HOST="${FC_MONITOR_LAN_TARGET_HOST:-127.0.0.1}"
LAN_PROXY_TARGET_PORT="${FC_MONITOR_LAN_TARGET_PORT:-7779}"
LAN_URL_STATE_FILE="${FC_MONITOR_LAN_URL_STATE_FILE:-${LOG_DIR}/monitor-lan-url.txt}"
PUBLIC_URL="${FC_MONITOR_PUBLIC_URL:-https://fc-monitor.loca.lt/api/status?lite=1}"
PUBLIC_HEADER_KEY="${FC_MONITOR_PUBLIC_HEADER_KEY:-bypass-tunnel-reminder}"
PUBLIC_HEADER_VALUE="${FC_MONITOR_PUBLIC_HEADER_VALUE:-1}"
PUBLIC_URL_STATE_FILE="${FC_MONITOR_PUBLIC_URL_STATE_FILE:-${LOG_DIR}/monitor-public-url.txt}"
TUNNEL_PROVIDER_STATE_FILE="${FC_MONITOR_TUNNEL_PROVIDER_STATE_FILE:-${LOG_DIR}/monitor-public-provider.txt}"
PUBLIC_FAILURE_STATE_FILE="${FC_MONITOR_PUBLIC_FAILURE_STATE_FILE:-${LOG_DIR}/monitor-public-fail-streak.txt}"
PUBLIC_FAILURE_THRESHOLD="${FC_MONITOR_PUBLIC_FAILURE_THRESHOLD:-2}"
LT_SUBDOMAIN="${FC_MONITOR_LT_SUBDOMAIN:-fc-monitor}"
LT_HOST="${FC_MONITOR_LT_HOST:-https://loca.lt}"
LT_PORT="${FC_MONITOR_LT_PORT:-7779}"
LOCALHOST_RUN_DEST="${FC_MONITOR_LOCALHOST_RUN_DEST:-nokey@localhost.run}"
TUNNEL_PROVIDERS="${FC_MONITOR_TUNNEL_PROVIDERS:-localtunnel,localhost_run}"
MANAGE_TUNNEL="${FC_MONITOR_MANAGE_TUNNEL:-0}"
ENFORCE_PUBLIC_ROOT_MATCH="${FC_MONITOR_ENFORCE_PUBLIC_ROOT_MATCH:-0}"
ENABLE_LAN_PROXY="${FC_MONITOR_ENABLE_LAN_PROXY:-1}"
FC_MONITOR_AUTO_START_STACK="${FC_MONITOR_AUTO_START_STACK:-0}"
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

heal_backend_if_needed() {
  if [[ ! -x "$BACKEND_HEAL_SCRIPT" && ! -f "$BACKEND_HEAL_SCRIPT" ]]; then
    log "backend_heal skipped: script missing path=$BACKEND_HEAL_SCRIPT"
    return 0
  fi
  set +e
  local output=""
  local rc=0
  output="$( (exec 9>&-; bash "$BACKEND_HEAL_SCRIPT") 2>&1 )"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    local detail=""
    detail="$(printf '%s' "$output" | tail -n 1 | tr '\n' ' ' | tr -s ' ' | cut -c1-180)"
    log "backend_heal ok detail=${detail:-none}"
    return 0
  fi
  local detail=""
  detail="$(printf '%s' "$output" | tail -n 3 | tr '\n' ' ' | tr -s ' ' | cut -c1-220)"
  log "backend_heal failed rc=${rc} detail=${detail:-none}"
  return 1
}

current_lan_url() {
  if [[ -n "${LAN_PROXY_HOST:-}" ]]; then
    printf 'http://%s:%s/\n' "$LAN_PROXY_HOST" "$LAN_PROXY_PORT"
    return 0
  fi
  printf 'http://127.0.0.1:%s/\n' "$LAN_PROXY_PORT"
}

current_lan_status_url() {
  if [[ -n "${LAN_PROXY_HOST:-}" ]]; then
    printf 'http://%s:%s/api/monitor/access\n' "$LAN_PROXY_HOST" "$LAN_PROXY_PORT"
    return 0
  fi
  printf 'http://127.0.0.1:%s/api/monitor/access\n' "$LAN_PROXY_PORT"
}

write_lan_url_state() {
  printf '%s\n' "$(current_lan_url)" > "$LAN_URL_STATE_FILE"
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

current_tunnel_provider() {
  local provider=""
  if [[ -f "$TUNNEL_PROVIDER_STATE_FILE" ]]; then
    provider="$(head -n 1 "$TUNNEL_PROVIDER_STATE_FILE" 2>/dev/null | tr -d '\r' | sed 's/^ *//; s/ *$//')"
  fi
  if [[ -n "$provider" ]]; then
    printf '%s\n' "$provider"
    return 0
  fi
  printf 'localtunnel\n'
}

write_tunnel_provider_state() {
  local provider="${1:-}"
  [[ -n "$provider" ]] || return 0
  printf '%s\n' "$provider" > "$TUNNEL_PROVIDER_STATE_FILE"
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
  pgrep -f 'apps/monitor/server.py|uvicorn.*7779' >/dev/null 2>&1 \
    || ss -ltn 2>/dev/null | awk '$4 ~ /:7779$/ {found=1} END{exit(found?0:1)}'
}

stack_process_running() {
  pgrep -f 'python.*run_api.py|uvicorn.*8050|http.server 5173|vite.*5173|apps/monitor/server.py' >/dev/null 2>&1
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
  local src_real=""
  local root_real=""
  src="$(public_queue_source)"
  [[ -n "$src" ]] || return 1
  src_real="$(readlink -f "$src" 2>/dev/null || printf '%s\n' "$src")"
  root_real="$(readlink -f "$ROOT" 2>/dev/null || printf '%s\n' "$ROOT")"
  [[ "$src" == "$ROOT"* ]] || [[ "$src_real" == "$root_real"* ]]
}

start_monitor_server() {
  local monitor_python="$MONITOR_PYTHON_BIN"
  if [[ ! -x "$monitor_python" ]]; then
    monitor_python="python3"
  fi
  (
    exec 9>&-
    nohup env FC_MONITOR_ROOT="$ROOT" "$monitor_python" "$MONITOR_APP_SCRIPT" >> "${LOG_DIR}/monitor-server.log" 2>&1 < /dev/null &
  )
  local _i=0
  while [[ "$_i" -lt 12 ]]; do
    if is_local_up; then
      return 0
    fi
    sleep 1
    _i=$((_i + 1))
  done
  return 1
}

restart_monitor_server() {
  pkill -f 'apps/monitor/server.py' >/dev/null 2>&1 || true
  sleep 2
  start_monitor_server
}

lan_proxy_running() {
  ss -ltn 2>/dev/null | awk -v host="${LAN_PROXY_HOST}" -v port="${LAN_PROXY_PORT}" '
    $4 == (host ":" port) { found=1 }
    END { exit(found ? 0 : 1) }
  '
}

is_lan_up() {
  curl -fsS -m 5 -o /dev/null "$(current_lan_status_url)" >/dev/null 2>&1
}

start_lan_proxy() {
  if [[ "$ENABLE_LAN_PROXY" != "1" ]]; then
    return 0
  fi
  if [[ -z "${LAN_PROXY_HOST:-}" ]] || [[ ! -f "$MONITOR_LAN_PROXY_SCRIPT" ]]; then
    log "lan proxy skipped host=${LAN_PROXY_HOST:-none} script_present=$( [[ -f "$MONITOR_LAN_PROXY_SCRIPT" ]] && echo 1 || echo 0 )"
    return 0
  fi
  (
    exec 9>&-
    setsid python3 "$MONITOR_LAN_PROXY_SCRIPT" \
      --listen-host "$LAN_PROXY_HOST" \
      --listen-port "$LAN_PROXY_PORT" \
      --target-host "$LAN_PROXY_TARGET_HOST" \
      --target-port "$LAN_PROXY_TARGET_PORT" >> "${LOG_DIR}/monitor-lan-proxy.log" 2>&1 < /dev/null &
  )
  sleep 1
  write_lan_url_state
}

stop_lan_proxy() {
  pkill -f 'monitor_lan_proxy.py' >/dev/null 2>&1 || true
}

restart_lan_proxy() {
  stop_lan_proxy
  sleep 1
  start_lan_proxy
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

start_localtunnel() {
  local mode="${1:-host}"
  local -a cmd=(npx --yes localtunnel --port "${LT_PORT}" --local-host 127.0.0.1)
  if [[ "$mode" == "host" ]]; then
    cmd+=(--subdomain "${LT_SUBDOMAIN}")
  fi
  if [[ -n "$LT_HOST" ]]; then
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
  elif [[ "$mode" == "host" ]]; then
    discovered_url="$(tail -n 40 "${LOG_DIR}/monitor-tunnel.log" 2>/dev/null | rg -o 'https://[a-z0-9-]+\.loca\.lt' | tail -n 1 || true)"
  fi

  if [[ "$mode" == "host" ]]; then
    write_public_url_state "$PUBLIC_URL"
  fi
  if [[ -n "$discovered_url" ]]; then
    if [[ "$mode" != "host" || "$discovered_url" == *"${LT_SUBDOMAIN}.loca.lt" ]]; then
      write_public_url_state "${discovered_url}/api/status?lite=1"
    fi
    log "tunnel url discovered mode=${mode} url=${discovered_url}"
  else
    log "tunnel url discovery pending provider=localtunnel mode=${mode}"
  fi
}

start_localhost_run() {
  local before_lines=0
  if [[ -f "${LOG_DIR}/monitor-tunnel.log" ]]; then
    before_lines="$(wc -l < "${LOG_DIR}/monitor-tunnel.log" 2>/dev/null || echo 0)"
    if ! [[ "$before_lines" =~ ^[0-9]+$ ]]; then
      before_lines=0
    fi
  fi

  (
    exec 9>&-
    nohup ssh \
      -o StrictHostKeyChecking=no \
      -o ServerAliveInterval=30 \
      -o TCPKeepAlive=yes \
      -o ExitOnForwardFailure=yes \
      -R "80:127.0.0.1:${LT_PORT}" \
      "${LOCALHOST_RUN_DEST}" >> "${LOG_DIR}/monitor-tunnel.log" 2>&1 < /dev/null &
  )
  sleep 6

  local discovered_url=""
  discovered_url="$(tail -n +"$((before_lines + 1))" "${LOG_DIR}/monitor-tunnel.log" 2>/dev/null | rg -o 'https://[a-z0-9.-]+' | tail -n 1 || true)"
  if [[ -n "$discovered_url" ]]; then
    write_public_url_state "${discovered_url}/api/status?lite=1"
    log "tunnel url discovered provider=localhost_run url=${discovered_url}"
  else
    log "tunnel url discovery pending provider=localhost_run"
  fi
}

start_tunnel() {
  local provider="${1:-localtunnel}"
  local mode="${2:-host}"
  write_tunnel_provider_state "$provider"
  case "$provider" in
    localtunnel)
      start_localtunnel "$mode"
      ;;
    localhost_run)
      start_localhost_run
      ;;
    *)
      log "unknown tunnel provider provider=${provider}"
      return 1
      ;;
  esac
}

localtunnel_pid_list() {
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

localhost_run_pid_list() {
  ps -eo pid=,args= 2>/dev/null | awk -v port="$LT_PORT" '
    {
      pid=$1
      $1=""
      line=substr($0,2)
      if (line ~ /monitor_stack_guard\.sh/) next
      if (line !~ /ssh/) next
      if (line !~ /localhost\.run/) next
      if (line !~ ("-R 80:127\\.0\\.0\\.1:" port)) next
      print pid
    }
  '
}

tunnel_pid_list() {
  {
    localtunnel_pid_list
    localhost_run_pid_list
  } | awk '!seen[$0]++'
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

clear_tunnel_state() {
  rm -f "$PUBLIC_URL_STATE_FILE" "$TUNNEL_PROVIDER_STATE_FILE" "$PUBLIC_FAILURE_STATE_FILE"
}

restart_tunnel() {
  stop_tunnel
  local provider=""
  local mode=""
  IFS=',' read -r -a providers <<< "$TUNNEL_PROVIDERS"
  for provider in "${providers[@]}"; do
    provider="$(printf '%s' "$provider" | sed 's/^ *//; s/ *$//')"
    [[ -n "$provider" ]] || continue
    case "$provider" in
      localtunnel)
        for mode in host plain; do
          log "restart tunnel provider=${provider} mode=${mode}"
          start_tunnel "$provider" "$mode"
          if tunnel_process_running && is_public_up; then
            log "tunnel healthy provider=${provider} mode=${mode} url=$(current_public_url)"
            write_public_fail_streak 0
            return 0
          fi
          stop_tunnel
        done
        ;;
      localhost_run)
        log "restart tunnel provider=${provider}"
        start_tunnel "$provider"
        if tunnel_process_running && is_public_up; then
          log "tunnel healthy provider=${provider} url=$(current_public_url)"
          write_public_fail_streak 0
          return 0
        fi
        stop_tunnel
        ;;
      *)
        log "skip unknown tunnel provider=${provider}"
        ;;
    esac
  done
  return 1
}

with_lock_or_exit

heal_backend_if_needed || true

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

if [[ "$ENABLE_LAN_PROXY" == "1" ]]; then
  write_lan_url_state
  if ! lan_proxy_running; then
    log "lan proxy missing; starting"
    start_lan_proxy
  fi
  if ! is_lan_up; then
    log "lan proxy down; restarting"
    restart_lan_proxy
  fi
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
    log "tunnel process missing; restarting across providers"
    restart_tunnel || true
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
  if tunnel_process_running; then
    log "public tunnels disabled; stopping active tunnel processes"
    stop_tunnel
  fi
  clear_tunnel_state
  if [[ "$ENABLE_LAN_PROXY" == "1" ]]; then
    log "ok local=up lan=$(is_lan_up && echo up || echo down) lan_url=$(current_lan_url) public=disabled"
  else
    log "ok local=up lan=disabled public=disabled"
  fi
fi
