#!/usr/bin/env bash
set -euo pipefail

# Start Dash UI in background and log output. Works from any CWD.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${AF_DASH_PORT:-8050}"
APP="$REPO_ROOT/src/dash_app/app.py"
LOGDIR="$REPO_ROOT/logs/dash"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/dash_${PORT}.log"
PIDFILE="$LOGDIR/dash_${PORT}.pid"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[dash] Port $PORT already in use. Refusing to start another instance." >&2
  echo "[dash] Hint: use 'make dash-stop' (or bash scripts/dash_stop.sh) to free the port." >&2
  echo "[dash] Current listeners:" >&2
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  exit 1
fi

echo "[dash-bg] Starting Dash on port $PORT (log: $LOGFILE) ..."
(
  echo "==== $(date '+%F %T') — dash start (port $PORT) ===="
  RUN_PY="$REPO_ROOT/.venv/bin/python3"
  if [ ! -x "$RUN_PY" ]; then
    echo "[dash-bg] ERROR: Virtual environment not properly set up.  Please run 'python3 -m venv .venv && source .venv/bin/activate'"
    exit 1
  fi
  AF_DASH_DEBUG=${AF_DASH_DEBUG:-false} PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src" exec "$RUN_PY" "$APP"
) >>"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "[dash-bg] PID $(cat "$PIDFILE")"
echo "[dash-bg] Tail logs: tail -f '$LOGFILE'"
