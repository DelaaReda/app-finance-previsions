#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
DISPATCHER="${ROOT}/platform/automation/admin_dispatcher_tick.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p \
  "$TMP_DIR/scripts" \
  "$TMP_DIR/platform" \
  "$TMP_DIR/docs/operations/orchestrator" \
  "$TMP_DIR/state/role-state" \
  "$TMP_DIR/state/dispatch" \
  "$TMP_DIR/logs"

cat > "$TMP_DIR/docs/operations/orchestrator/priority-queue.json" <<'JSON'
{
  "version": "test",
  "items": [
    {"id": "BATCH-10", "state": "IN_PROGRESS"}
  ]
}
JSON

cat > "$TMP_DIR/docs/operations/orchestrator/parallel-workstreams.json" <<'JSON'
{
  "version": "test",
  "streams": [{"id": "BATCH-10", "state": "IN_PROGRESS"}],
  "tasks": [
    {
      "id": "BATCH-10-DEV-01",
      "stream_id": "BATCH-10",
      "role": "dev",
      "state": "IN_PROGRESS",
      "assignee": "dev",
      "handoff_to": ""
    }
  ],
  "handoffs": []
}
JSON

cat > "$TMP_DIR/docs/operations/orchestrator/executors-monitoring-latest.json" <<'JSON'
{"roles": {}, "summary": {}}
JSON

cat > "$TMP_DIR/state/role-state/dev.last_contract" <<'EOF_CONTRACT'
STATUS: IN_PROGRESS
DELTA: NO_DELTA
EVIDENCE: task_id=BATCH-10-DEV-01; stream_id=BATCH-10; task_update=none_no_signal
EOF_CONTRACT

cat > "$TMP_DIR/state/role-state/planner.last_contract" <<'EOF_CONTRACT'
STATUS: WAIT
DELTA: NO_DELTA
EVIDENCE: task_update=none_no_signal
EOF_CONTRACT

run_dispatch() {
  FC_WORKSPACE_ROOT="$TMP_DIR" \
  FC_ADMIN_DISPATCH_QUEUE_FILE="$TMP_DIR/docs/operations/orchestrator/priority-queue.json" \
  FC_ADMIN_DISPATCH_BOARD_FILE="$TMP_DIR/docs/operations/orchestrator/parallel-workstreams.json" \
  FC_ADMIN_DISPATCH_EXEC_FILE="$TMP_DIR/docs/operations/orchestrator/executors-monitoring-latest.json" \
  FC_ADMIN_DISPATCH_STATE_DIR="$TMP_DIR/state/dispatch" \
  FC_ROLE_STATE_DIR="$TMP_DIR/state/role-state" \
  FC_ADMIN_DISPATCH_LOG_FILE="$TMP_DIR/logs/admin.dispatch.log" \
  FC_ADMIN_DISPATCH_TICK_LOG="$TMP_DIR/logs/admin.tick.log" \
  FC_ADMIN_DISPATCH_ENABLED=1 \
  FC_ADMIN_AUTONOMY_ENABLED=1 \
  FC_ADMIN_STALL_TICKS_THRESHOLD=2 \
  FC_ADMIN_AUTONOMY_MAX_ACTIONS=2 \
  FC_ADMIN_DISPATCH_DRY_RUN=1 \
  AGENT_MESSAGE_BUS_ENABLED=0 \
  bash "$DISPATCHER"
}

OUT1="$(run_dispatch || true)"
OUT2="$(run_dispatch || true)"

[[ "$OUT1" == *"status=NOOP"* ]] || {
  echo "Expected first run to be NOOP"
  exit 1
}
[[ "$OUT2" == *"autonomy_trigger=stalled_lane"* ]] || {
  echo "Expected second run to trigger stalled_lane autonomy"
  exit 1
}

STATE_FILE="$TMP_DIR/state/role-state/admin_autonomy_state.json"
[[ -f "$STATE_FILE" ]] || {
  echo "Missing autonomy state file"
  exit 1
}

python3 - "$STATE_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
state = json.loads(path.read_text(encoding="utf-8"))
assert state.get("active") is True
assert state.get("trigger") == "stalled_lane"
assert state.get("target_role") == "dev"
assert int(state.get("streak_by_role", {}).get("dev", 0)) >= 2
print("OK")
PY

echo "PASS test_admin_autonomy_e2e"
