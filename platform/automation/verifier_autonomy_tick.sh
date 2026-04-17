#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "VERIFIER_AUTONOMY status=soft_fail reason=workspace_helper_missing"
  exit 0
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

STATE_DIR="${FC_ROLE_STATE_DIR:-${TMUX_ROLE_STATE_DIR:-${HOME}/.openclaw/cron/role-state}}"
STATE_FILE="${FC_VERIFIER_AUTONOMY_STATE_FILE:-${STATE_DIR}/verifier_autonomy_state.json}"
LOCK_FILE="${STATE_FILE}.lock"
LOG_FILE="${FC_VERIFIER_AUTONOMY_LOG_FILE:-${ROOT}/logs-codex-runs/fc-ticks/verifier.autonomy.log}"
BACKOFF_MINUTES="${FC_VERIFIER_BACKOFF_MINUTES:-20}"
NULL_STREAK_THRESHOLD="${FC_VERIFIER_NULL_STREAK_THRESHOLD:-3}"

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"

ts_utc() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

log_line() {
  printf '%s %s\n' "$(ts_utc)" "$*" >> "$LOG_FILE"
}

with_lock() {
  if command -v flock >/dev/null 2>&1; then
    exec 73>"$LOCK_FILE"
    flock -n 73 || {
      echo "VERIFIER_AUTONOMY status=skip reason=busy_lock"
      exit 0
    }
    return 0
  fi
  local lock_dir="${LOCK_FILE}.d"
  if ! mkdir "$lock_dir" 2>/dev/null; then
    echo "VERIFIER_AUTONOMY status=skip reason=busy_lock"
    exit 0
  fi
  trap 'rmdir "'"$lock_dir"'" 2>/dev/null || true' EXIT
}

delivery_snapshot() {
  python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
path = root / "logs-codex-runs" / "orchestrator-state" / "product_delivery_state.json"
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    payload = {}
current_public = payload.get("current_public_proof") if isinstance(payload.get("current_public_proof"), dict) else {}
print(
    "|".join(
        [
            str(payload.get("phase") or "unknown"),
            str(payload.get("active_batch_id") or "none"),
            str(payload.get("public_proof_status") or "unknown"),
            str(current_public.get("proof_ref") or "none"),
            str(payload.get("last_meaningful_delta_at") or "none"),
            "1" if bool(payload.get("ec2_reachable", False)) else "0",
        ]
    )
)
PY
}

state_field() {
  local field="$1"
  python3 - "$STATE_FILE" "$field" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    payload = {}
value = payload.get(field, "")
if isinstance(value, bool):
    print("1" if value else "0")
elif value is None:
    print("")
else:
    print(str(value))
PY
}

write_state() {
  local batch_id="$1"
  local phase="$2"
  local public_status="$3"
  local proof_ref="$4"
  local last_delta="$5"
  local streak="$6"
  local reason="$7"
  python3 - "$STATE_FILE" "$batch_id" "$phase" "$public_status" "$proof_ref" "$last_delta" "$streak" "$reason" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "last_batch_id": sys.argv[2] or None,
    "last_phase": sys.argv[3] or None,
    "last_status": sys.argv[4] or None,
    "last_proof_ref": sys.argv[5] or None,
    "last_meaningful_delta_at": sys.argv[6] or None,
    "null_tick_streak": int(sys.argv[7] or "0"),
    "reason": sys.argv[8] or "none",
    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
}

set_backoff() {
  local batch_id="$1"
  local phase="$2"
  local reason="$3"
  local streak="$4"
  python3 - "$ROOT" "$BACKOFF_MINUTES" "$batch_id" "$phase" "$reason" "$streak" <<'PY'
import sys
from datetime import datetime, timedelta, timezone

from runtime.truth.lane_backoff import write_lane_backoff

root = sys.argv[1]
minutes = max(1, int(sys.argv[2] or "20"))
now = datetime.now(timezone.utc)
until = now + timedelta(minutes=minutes)
write_lane_backoff(
    root,
    "verifier",
    {
        "active": True,
        "reason": sys.argv[5] or "verifier_no_change_streak",
        "trigger_streak": int(sys.argv[6] or "0"),
        "batch_id": sys.argv[3] or None,
        "phase": sys.argv[4] or None,
        "until": until.isoformat().replace("+00:00", "Z"),
        "until_epoch": int(until.timestamp()),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    },
)
PY
}

clear_backoff() {
  local reason="$1"
  python3 - "$ROOT" "$reason" <<'PY'
import sys
from runtime.truth.lane_backoff import clear_lane_backoff

clear_lane_backoff(sys.argv[1], "verifier", reason=sys.argv[2] or "cleared")
PY
}

backoff_snapshot() {
  python3 - "$ROOT" <<'PY'
import sys
from runtime.truth.lane_backoff import load_lane_backoff, is_lane_backoff_active

payload = load_lane_backoff(sys.argv[1], "verifier")
active = is_lane_backoff_active(payload)
print(
    "|".join(
        [
            "1" if active else "0",
            str(payload.get("batch_id") or "none"),
            str(payload.get("phase") or "none"),
            str(payload.get("reason") or "none"),
            str(payload.get("trigger_streak") or 0),
        ]
    )
)
PY
}

run_public_proof() {
  local batch_id="$1"
  python3 platform/automation/runtime/planner/planner_runtime_actions.py public-proof --root "$ROOT" --batch-id "$batch_id" --if-needed
}

with_lock

snapshot="$(delivery_snapshot)"
phase="${snapshot%%|*}"
rest="${snapshot#*|}"
batch_id="${rest%%|*}"
rest="${rest#*|}"
public_status="${rest%%|*}"
rest="${rest#*|}"
proof_ref="${rest%%|*}"
rest="${rest#*|}"
last_delta="${rest%%|*}"
ec2_reachable="${rest##*|}"

backoff="$(backoff_snapshot)"
backoff_active="${backoff%%|*}"
backoff_rest="${backoff#*|}"
backoff_batch="${backoff_rest%%|*}"
backoff_rest="${backoff_rest#*|}"
backoff_phase="${backoff_rest%%|*}"
backoff_rest="${backoff_rest#*|}"
backoff_reason="${backoff_rest%%|*}"
backoff_streak="${backoff_rest##*|}"

if [[ "$backoff_active" == "1" ]]; then
  if [[ "$batch_id" != "$backoff_batch" || "$phase" != "$backoff_phase" ]]; then
    clear_backoff "state_changed"
    log_line "verifier_backoff_cleared reason=state_changed batch_id=${batch_id} phase=${phase}"
  else
    log_line "verifier_backoff_skip reason=${backoff_reason} streak=${backoff_streak} batch_id=${batch_id} phase=${phase}"
    echo "VERIFIER_AUTONOMY status=skip reason=lane_backoff_active batch_id=${batch_id:-none} phase=${phase:-unknown} trigger_streak=${backoff_streak:-0}"
    exit 0
  fi
fi

last_batch_id="$(state_field last_batch_id)"
last_phase="$(state_field last_phase)"
last_status="$(state_field last_status)"
last_proof_ref="$(state_field last_proof_ref)"
last_meaningful_delta="$(state_field last_meaningful_delta_at)"
null_tick_streak="$(state_field null_tick_streak)"
if ! [[ "$null_tick_streak" =~ ^[0-9]+$ ]]; then
  null_tick_streak=0
fi

if [[ "$phase" != "verifying_public_proof" || -z "$batch_id" || "$batch_id" == "none" ]]; then
  write_state "$batch_id" "$phase" "$public_status" "$proof_ref" "$last_delta" "0" "idle_or_non_verifying_phase"
  echo "VERIFIER_AUTONOMY status=skip reason=idle_or_non_verifying_phase batch_id=${batch_id:-none} phase=${phase:-unknown}"
  exit 0
fi

should_run=0
run_reason="no_change"
if [[ "$batch_id" != "$last_batch_id" ]]; then
  should_run=1
  run_reason="batch_changed"
elif [[ "$phase" != "$last_phase" ]]; then
  should_run=1
  run_reason="phase_changed"
elif [[ "$last_delta" != "$last_meaningful_delta" ]]; then
  should_run=1
  run_reason="meaningful_delta_changed"
elif [[ "$public_status" == "error" ]]; then
  should_run=1
  run_reason="public_proof_error"
elif [[ "$last_status" == "maintenance" || "$last_status" == "error" || "$last_status" == "deferred" ]]; then
  should_run=1
  run_reason="retry_after_non_ok"
elif [[ "$proof_ref" != "$last_proof_ref" && "$proof_ref" != "none" ]]; then
  should_run=1
  run_reason="proof_ref_changed"
fi

if [[ "$public_status" == "ok" && "$proof_ref" != "none" && "$should_run" != "1" ]]; then
  write_state "$batch_id" "$phase" "$public_status" "$proof_ref" "$last_delta" "0" "proof_already_ok"
  echo "VERIFIER_AUTONOMY status=skip reason=proof_already_ok batch_id=${batch_id} phase=${phase}"
  exit 0
fi

if [[ "$should_run" != "1" ]]; then
  null_tick_streak=$(( null_tick_streak + 1 ))
  write_state "$batch_id" "$phase" "$public_status" "$proof_ref" "$last_delta" "$null_tick_streak" "no_change"
  if (( null_tick_streak >= NULL_STREAK_THRESHOLD )); then
    set_backoff "$batch_id" "$phase" "verifier_no_change_streak" "$null_tick_streak"
    log_line "verifier_backoff_set reason=verifier_no_change_streak streak=${null_tick_streak} batch_id=${batch_id} phase=${phase}"
  fi
  echo "VERIFIER_AUTONOMY status=skip reason=no_change batch_id=${batch_id} phase=${phase} trigger_streak=${null_tick_streak}"
  exit 0
fi

clear_backoff "triggered_run"
set +e
proof_output="$(run_public_proof "$batch_id" 2>&1)"
proof_rc=$?
set -e
printf '%s\n' "$proof_output" >> "$LOG_FILE"
if [[ "$proof_rc" -ne 0 ]]; then
  write_state "$batch_id" "$phase" "error" "$proof_ref" "$last_delta" "0" "public_proof_runner_failed"
  echo "VERIFIER_AUTONOMY status=error reason=public_proof_runner_failed batch_id=${batch_id} phase=${phase}"
  exit 0
fi

proof_status="$(printf '%s\n' "$proof_output" | sed -n 's/^PUBLIC_PROOF\(_SKIP\)\{0,1\} .*status=\([^[:space:]]*\).*/\2/p' | tail -1)"
proof_ref_new="$(printf '%s\n' "$proof_output" | sed -n 's/^PUBLIC_PROOF\(_SKIP\)\{0,1\} .*proof_ref=\([^[:space:]]*\).*/\2/p' | tail -1)"
proof_status="${proof_status:-unknown}"
proof_ref_new="${proof_ref_new:-$proof_ref}"
write_state "$batch_id" "$phase" "$proof_status" "$proof_ref_new" "$last_delta" "0" "$run_reason"
log_line "verifier_public_proof_run reason=${run_reason} batch_id=${batch_id} proof_status=${proof_status} proof_ref=${proof_ref_new}"
echo "VERIFIER_AUTONOMY status=ok reason=${run_reason} batch_id=${batch_id} phase=${phase} proof_status=${proof_status} proof_ref=${proof_ref_new}"
