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
  # Optional OpenTelemetry auto-instrumentation
  # Enable by exporting AF_DASH_OTEL=1 (and OTEL_* envs as needed)
  if [ "${AF_DASH_OTEL:-0}" = "1" ]; then
    if command -v opentelemetry-instrument >/dev/null 2>&1; then
      : "${OTEL_SERVICE_NAME:=af-dash}"
      : "${OTEL_TRACES_EXPORTER:=otlp}"
      : "${OTEL_METRICS_EXPORTER:=otlp}"
      : "${OTEL_LOGS_EXPORTER:=otlp}"
      : "${OTEL_EXPORTER_OTLP_ENDPOINT:=http://127.0.0.1:4318}"
      : "${OTEL_PYTHON_LOG_CORRELATION:=true}"
      : "${OTEL_RESOURCE_ATTRIBUTES:=deployment.environment=dev}"
      echo "[dash-bg] OpenTelemetry enabled (endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT})"
      AF_DASH_DEBUG=${AF_DASH_DEBUG:-false} PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src" exec opentelemetry-instrument "$RUN_PY" "$APP"
    else
      echo "[dash-bg] WARNING: AF_DASH_OTEL=1 but 'opentelemetry-instrument' not found. Starting without OTel." >&2
      AF_DASH_DEBUG=${AF_DASH_DEBUG:-false} PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src" exec "$RUN_PY" "$APP"
    fi
  else
    AF_DASH_DEBUG=${AF_DASH_DEBUG:-false} PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src" exec "$RUN_PY" "$APP"
  fi
) >>"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "[dash-bg] PID $(cat "$PIDFILE")"
echo "[dash-bg] Tail logs: tail -f '$LOGFILE'"
