#!/usr/bin/env bash
set -euo pipefail

# Stop Streamlit instance(s) for a specific app path
# Usage: AF_UI_APP=src/apps/forecast_app.py bash scripts/ui_stop_app.sh

APP="${AF_UI_APP:-}"
if [ -z "$APP" ]; then
  echo "[ui-stop-app] AF_UI_APP not set (e.g. src/apps/forecast_app.py)" >&2
  exit 1
fi

PIDS=$(pgrep -f "streamlit run .*${APP}" || true)
if [ -z "$PIDS" ]; then
  echo "[ui-stop-app] No Streamlit instance found for $APP"
  exit 0
fi

echo "[ui-stop-app] Stopping PIDs: $PIDS for $APP"
kill $PIDS || true
sleep 1
kill -9 $PIDS 2>/dev/null || true
echo "[ui-stop-app] Done."

