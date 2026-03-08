#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
COPILOT="${ROOT}/apps/api/runtime/copilot.sh"
TMP_DIR="$(mktemp -d)"
PID_FILE="$TMP_DIR/frontend.pid"
PORT=35173

cleanup() {
  pkill -f "http.server ${PORT}" 2>/dev/null || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cd "$TMP_DIR"
FC_COPILOT_SOURCE_ONLY=1 source "$COPILOT"

if command -v setsid >/dev/null 2>&1; then
  setsid python3 -m http.server "$PORT" </dev/null >"$TMP_DIR/frontend.log" 2>&1 &
else
  nohup python3 -m http.server "$PORT" </dev/null >"$TMP_DIR/frontend.log" 2>&1 &
fi
WRAPPER_PID=$!

for _ in {1..20}; do
  if curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

ACTUAL_PID="$(listener_pid_for_port "$PORT")"
persist_listener_pid "$PORT" "$PID_FILE" 999999
RECORDED_PID="$(cat "$PID_FILE")"

[[ "$ACTUAL_PID" =~ ^[0-9]+$ ]]
[[ "$RECORDED_PID" =~ ^[0-9]+$ ]]
[[ "$RECORDED_PID" == "$ACTUAL_PID" ]]
[[ "$RECORDED_PID" != "999999" ]]
kill -0 "$RECORDED_PID"

echo "PASS test_runtime_launcher_frontend_pid"
