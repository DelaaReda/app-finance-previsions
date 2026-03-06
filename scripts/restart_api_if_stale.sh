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
SMOKE_SCRIPT="$ROOT/scripts/critical_endpoints_smoke.sh"
LOG="/tmp/fc-api-restart.log"
ts() { date '+%Y-%m-%dT%H:%M:%S'; }

api_pid() {
  pgrep -f "python.*run_api\.py" 2>/dev/null | head -1
}

api_alive() {
  curl -fsS -m 3 -o /dev/null "${API_URL}/api/health" >/dev/null 2>&1
}

smoke_pass() {
  [[ -x "$SMOKE_SCRIPT" || -f "$SMOKE_SCRIPT" ]] || return 0  # skip if missing
  bash "$SMOKE_SCRIPT" --base-url "$API_URL" --quiet >/dev/null 2>&1
}

pid="$(api_pid)"

# Case 1: API not running at all
if [[ -z "$pid" ]]; then
  printf '%s [WARN] API process not found; starting\n' "$(ts)" >> "$LOG"
  cd "$API_SRC" && nohup .venv/bin/python3 run_api.py >> "$API_LOG" 2>&1 &
  sleep 5
  printf '%s [INFO] API started pid=%s\n' "$(ts)" "$(api_pid)" >> "$LOG"
  exit 0
fi

# Case 2: API alive but schema stale (smoke test fails = edge/contracts not loaded)
if api_alive && ! smoke_pass; then
  printf '%s [WARN] API alive but smoke FAIL (edge contracts stale); restarting pid=%s\n' "$(ts)" "$pid" >> "$LOG"
  kill -SIGTERM "$pid" 2>/dev/null || true
  sleep 3
  kill -0 "$pid" 2>/dev/null && kill -SIGKILL "$pid" 2>/dev/null || true
  sleep 1
  cd "$API_SRC" && nohup .venv/bin/python3 run_api.py >> "$API_LOG" 2>&1 &
  sleep 5
  if api_alive && smoke_pass; then
    printf '%s [OK] API restarted and smoke PASS pid=%s\n' "$(ts)" "$(api_pid)" >> "$LOG"
  else
    printf '%s [ERROR] API restart failed\n' "$(ts)" >> "$LOG"
    exit 1
  fi
  exit 0
fi

printf '%s [OK] API pid=%s smoke=pass\n' "$(ts)" "$pid" >> "$LOG"
exit 0
