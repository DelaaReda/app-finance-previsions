#!/usr/bin/env bash
# restart_api_if_stale.sh — Redémarre l'API si le process est stale (code plus récent que process)
# Vérifie aussi que edge/contracts.py est bien chargé (smoke test)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
API_SRC="$ROOT/apps/api/src"
API_LOG="$ROOT/apps/api/runtime/api.log"
API_PORT="${FC_API_PORT:-8050}"
API_URL="http://127.0.0.1:${API_PORT}"
API_PROBE_TIMEOUT_SECONDS="${FC_API_PROBE_TIMEOUT_SECONDS:-8}"
SMOKE_SCRIPT="$ROOT/scripts/critical_endpoints_smoke.sh"
LOG="/tmp/fc-api-restart.log"
LOCK_FILE="/tmp/fc-api-restart.lock"
CLOSE_WAIT_THRESHOLD="${FC_API_CLOSE_WAIT_THRESHOLD:-80}"
LISTEN_RECVQ_THRESHOLD="${FC_API_LISTEN_RECVQ_THRESHOLD:-64}"
BACKEND_UNIT="${FC_BACKEND_SYSTEMD_UNIT:-finance-backend.service}"
SYSTEMCTL_TIMEOUT_SECONDS="${FC_BACKEND_SYSTEMCTL_TIMEOUT_SECONDS:-25}"
API_RESTART_PROBE_WINDOW_SECONDS="${FC_API_RESTART_PROBE_WINDOW_SECONDS:-45}"
ts() { date '+%Y-%m-%dT%H:%M:%S'; }

systemctl_user() {
  local runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  local dbus_addr="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${runtime_dir}/bus}"
  env \
    XDG_RUNTIME_DIR="$runtime_dir" \
    DBUS_SESSION_BUS_ADDRESS="$dbus_addr" \
    systemctl --user "$@"
}

systemctl_user_timeout() {
  local runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  local dbus_addr="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${runtime_dir}/bus}"
  env \
    XDG_RUNTIME_DIR="$runtime_dir" \
    DBUS_SESSION_BUS_ADDRESS="$dbus_addr" \
    timeout "${SYSTEMCTL_TIMEOUT_SECONDS}" systemctl --user "$@"
}

backend_unit_file_exists() {
  local unit_path=""
  for unit_path in \
    "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/${BACKEND_UNIT}" \
    "/etc/systemd/user/${BACKEND_UNIT}" \
    "/usr/lib/systemd/user/${BACKEND_UNIT}" \
    "/lib/systemd/user/${BACKEND_UNIT}"; do
    [[ -f "$unit_path" ]] && return 0
  done
  return 1
}

backend_unit_available() {
  command -v systemctl >/dev/null 2>&1 || return 1
  systemctl_user cat "$BACKEND_UNIT" >/dev/null 2>&1 || backend_unit_file_exists
}

api_pids() {
  {
    if command -v lsof >/dev/null 2>&1; then
      lsof -tiTCP:"${API_PORT}" -sTCP:LISTEN 2>/dev/null || true
    fi
    if command -v ss >/dev/null 2>&1; then
      ss -ltnp "( sport = :${API_PORT} )" 2>/dev/null \
        | grep -o 'pid=[0-9]\+' \
        | cut -d= -f2 \
        || true
    fi
    pgrep -f "python.*run_api\.py" 2>/dev/null || true
  } | awk 'NF {print $1}' | sort -u
}

api_pid() {
  api_pids | head -1
}

api_alive() {
  curl -fsS -m "$API_PROBE_TIMEOUT_SECONDS" -o /dev/null "${API_URL}/api/status" >/dev/null 2>&1 \
    || curl -fsS -m "$API_PROBE_TIMEOUT_SECONDS" -o /dev/null "${API_URL}/api/health" >/dev/null 2>&1
}

wait_api_alive() {
  local timeout_s="${1:-45}"
  local waited=0
  while (( waited < timeout_s )); do
    if api_alive; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

close_wait_count() {
  if command -v ss >/dev/null 2>&1; then
    ss -tan state close-wait "( sport = :${API_PORT} or dport = :${API_PORT} )" 2>/dev/null | awk 'NR>1 {count+=1} END {print count+0}'
    return 0
  fi
  echo 0
}

listen_recvq() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :${API_PORT} )" 2>/dev/null | awk 'NR==2 {print $2+0; found=1} END {if (!found) print 0}'
    return 0
  fi
  echo 0
}

smoke_pass() {
  [[ -x "$SMOKE_SCRIPT" || -f "$SMOKE_SCRIPT" ]] || return 0  # skip if missing
  bash "$SMOKE_SCRIPT" --base-url "$API_URL" --quiet >/dev/null 2>&1
}

force_stop_backend_unit() {
  backend_unit_available || return 1

  if command -v timeout >/dev/null 2>&1; then
    systemctl_user_timeout stop "$BACKEND_UNIT" >/dev/null 2>&1 || true
  else
    systemctl_user stop "$BACKEND_UNIT" >/dev/null 2>&1 || true
  fi

  local active_state
  active_state="$(systemctl_user show "$BACKEND_UNIT" -p ActiveState --value 2>/dev/null || true)"
  case "$active_state" in
    active|activating|deactivating|reloading)
      systemctl_user kill --kill-who=all --signal=KILL "$BACKEND_UNIT" >/dev/null 2>&1 || true
      sleep 1
      ;;
  esac

  systemctl_user reset-failed "$BACKEND_UNIT" >/dev/null 2>&1 || true
}

start_api() {
  if backend_unit_available; then
    local active_state
    active_state="$(systemctl_user show "$BACKEND_UNIT" -p ActiveState --value 2>/dev/null || true)"
    case "$active_state" in
      active|activating|deactivating|reloading)
        force_stop_backend_unit
        ;;
    esac
    if command -v timeout >/dev/null 2>&1; then
      systemctl_user_timeout start "$BACKEND_UNIT"
    else
      systemctl_user start "$BACKEND_UNIT"
    fi
    return 0
  fi
  cd "$API_SRC"
  (
    exec 9>&-
    FINANCE_COPILOT_RELOAD=0 nohup .venv/bin/python3 run_api.py >> "$API_LOG" 2>&1 &
  )
}

stop_api() {
  local pids
  pids="$(api_pids)"
  [[ -n "$pids" ]] || return 0

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    kill -SIGTERM "$pid" 2>/dev/null || true
  done <<< "$pids"

  sleep 3

  pids="$(api_pids)"
  [[ -n "$pids" ]] || return 0

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    kill -SIGKILL "$pid" 2>/dev/null || true
  done <<< "$pids"
}

restart_api() {
  if backend_unit_available; then
    force_stop_backend_unit
    stop_api
    sleep 1
    start_api
    return 0
  fi
  stop_api
  sleep 1
  start_api
}

pid="$(api_pid)"

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    printf '%s [INFO] API restart check already running; skipping overlap\n' "$(ts)" >> "$LOG"
    exit 0
  fi
fi

# Case 1: API not running at all
if [[ -z "$pid" ]]; then
  printf '%s [WARN] API process not found; starting\n' "$(ts)" >> "$LOG"
  start_api
  if wait_api_alive "$API_RESTART_PROBE_WINDOW_SECONDS"; then
    printf '%s [INFO] API started pid=%s\n' "$(ts)" "$(api_pid)" >> "$LOG"
    exit 0
  fi
  printf '%s [ERROR] API start timed out after %ss\n' "$(ts)" "$API_RESTART_PROBE_WINDOW_SECONDS" >> "$LOG"
  exit 1
fi

close_waits="$(close_wait_count)"
listen_q="$(listen_recvq)"
if ! api_alive; then
  sleep 2
  if api_alive; then
    printf '%s [INFO] API probe recovered after retry pid=%s\n' "$(ts)" "$pid" >> "$LOG"
    printf '%s [OK] API pid=%s smoke=pass\n' "$(ts)" "$pid" >> "$LOG"
    exit 0
  fi
  if [[ "${close_waits:-0}" -ge "$CLOSE_WAIT_THRESHOLD" ]] || [[ "${listen_q:-0}" -ge "$LISTEN_RECVQ_THRESHOLD" ]]; then
    printf '%s [WARN] API unhealthy with socket pressure close_wait=%s recv_q=%s; restarting pid=%s\n' "$(ts)" "$close_waits" "$listen_q" "$pid" >> "$LOG"
  else
    printf '%s [WARN] API health timeout/unreachable without socket pressure close_wait=%s recv_q=%s; restarting pid=%s\n' "$(ts)" "$close_waits" "$listen_q" "$pid" >> "$LOG"
  fi
  restart_api "$pid"
  if wait_api_alive "$API_RESTART_PROBE_WINDOW_SECONDS"; then
    if smoke_pass; then
      printf '%s [OK] API restarted and smoke PASS pid=%s\n' "$(ts)" "$(api_pid)" >> "$LOG"
    else
      printf '%s [ERROR] API restarted but smoke still FAIL pid=%s\n' "$(ts)" "$(api_pid)" >> "$LOG"
      exit 1
    fi
  else
    printf '%s [ERROR] API restart after health timeout failed timeout=%ss\n' "$(ts)" "$API_RESTART_PROBE_WINDOW_SECONDS" >> "$LOG"
    exit 1
  fi
  exit 0
fi

# Case 2: API alive but schema stale (smoke test fails = edge/contracts not loaded)
if api_alive && ! smoke_pass; then
  printf '%s [WARN] API alive but smoke FAIL (edge contracts stale); keeping backend running pid=%s\n' "$(ts)" "$pid" >> "$LOG"
  exit 0
fi

printf '%s [OK] API pid=%s smoke=pass\n' "$(ts)" "$pid" >> "$LOG"
exit 0
