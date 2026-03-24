#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
RUNTIME_HOST_GUARD="${SCRIPT_DIR}/../platform/automation/lib/runtime_host_guard.sh"
if [[ ! -f "$WORKSPACE_HELPER" || ! -f "$RUNTIME_HOST_GUARD" ]]; then
  echo "planner_companion_tick: missing workspace/runtime helpers" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"
# shellcheck source=/dev/null
source "$RUNTIME_HOST_GUARD"

fc_runtime_assert_vm_or_exit "planner_companion_tick"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
STATE_DIR="${ROOT}/logs-codex-runs/orchestrator-state"
STATE_FILE="${STATE_DIR}/planner-companion-state.json"
BOARD_RUNTIME_HELPER="${ROOT}/platform/automation/runtime/planner/planner_board_runtime.py"
DIRECTIVE_BUS="${ROOT}/platform/automation/directive_bus.sh"
PLANNER_TICK_LOG="${ROOT}/logs-codex-runs/ops/planner-companion-launch.log"
PLANNER_KICK_COOLDOWN_SECONDS="${FC_PLANNER_COMPANION_KICK_COOLDOWN_SECONDS:-900}"
PLANNER_ACTIVE_STALE_SECONDS="${FC_PLANNER_COMPANION_ACTIVE_STALE_SECONDS:-900}"
PLANNER_IDLE_STALE_SECONDS="${FC_PLANNER_COMPANION_IDLE_STALE_SECONDS:-600}"

mkdir -p "$STATE_DIR" "${ROOT}/logs-codex-runs/ops"

BOARD_SNAPSHOT_FILE="$(mktemp /tmp/planner-companion-board.XXXXXX.json)"
python3 "$BOARD_RUNTIME_HELPER" --root "$ROOT" snapshot >"$BOARD_SNAPSHOT_FILE"

PAYLOAD="$(
python3 - "$ROOT" "$STATE_FILE" "$PLANNER_KICK_COOLDOWN_SECONDS" "$PLANNER_ACTIVE_STALE_SECONDS" "$PLANNER_IDLE_STALE_SECONDS" "$BOARD_SNAPSHOT_FILE" <<'PY'
import hashlib
import json
import os
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
state_file = Path(sys.argv[2])
kick_cooldown_s = max(60, int(sys.argv[3]))
active_stale_s = max(120, int(sys.argv[4]))
idle_stale_s = max(120, int(sys.argv[5]))
snapshot_file = Path(sys.argv[6])
now = int(time.time())


def read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def state_age_s(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    return max(0, now - int(path.stat().st_mtime))


def normalize_issue_token(value: str) -> str:
    return "_".join(value.split()).strip(" _").lower() or "none"


snapshot = read_json(snapshot_file)
active_subagent_ids = snapshot.get("active_subagent_ids") if isinstance(snapshot.get("active_subagent_ids"), list) else []
subagent_progress_age = int(snapshot.get("subagent_progress_age_s", -1) or -1)
if subagent_progress_age < 0:
    subagent_progress_age = None
active_strategy_task = snapshot.get("active_planner_task") if isinstance(snapshot.get("active_planner_task"), dict) else {}
if not str(active_strategy_task.get("task_id", "")).strip() or str(active_strategy_task.get("task_id", "")).strip() == "none":
    active_strategy_task = None
ready_planner_task = snapshot.get("ready_planner_task") if isinstance(snapshot.get("ready_planner_task"), dict) else {}
if not str(ready_planner_task.get("task_id", "")).strip() or str(ready_planner_task.get("task_id", "")).strip() == "none":
    ready_planner_task = None
dev_ready_count = int(snapshot.get("ready_dev_count", 0) or 0)
board_path_value = str(snapshot.get("workboard_file") or "").strip()
registry_path_value = str(snapshot.get("registry_file") or "").strip()
events_path_value = str(snapshot.get("events_file") or "").strip()
board_path = Path(board_path_value) if board_path_value and board_path_value != "none" else None
registry_path = Path(registry_path_value) if registry_path_value and registry_path_value != "none" else None
events_path = Path(events_path_value) if events_path_value and events_path_value != "none" else None

guardian_candidates = [
    root / "logs-codex-runs" / "orchestrator-state" / "planner-guardian-latest.json",
    root / "docs" / "operations" / "orchestrator" / "planner-guardian-latest.json",
    root / "docs" / "orchestrator-ops" / "planner-guardian-latest.json",
]
guardian_path = next((path for path in guardian_candidates if path.exists()), None)
guardian = read_json(guardian_path) if guardian_path else {}
registry_age = state_age_s(registry_path)
events_age = state_age_s(events_path)

role_state_dir = Path(
    os.environ.get("FC_ROLE_STATE_DIR")
    or os.environ.get("TMUX_ROLE_STATE_DIR")
    or (Path.home() / ".openclaw" / "cron" / "role-state")
)
contract_path = role_state_dir / "planner.last_contract"
contract_age = state_age_s(contract_path)
guardian_age = state_age_s(guardian_path)

issues = guardian.get("issues") if isinstance(guardian.get("issues"), list) else []
issues = [normalize_issue_token(str(item)) for item in issues if str(item).strip()]
recommendations = guardian.get("recommendations") if isinstance(guardian.get("recommendations"), list) else []
recommendations = [str(item).strip() for item in recommendations if str(item).strip()]
summary = guardian.get("summary") if isinstance(guardian.get("summary"), dict) else {}
next_action = str(summary.get("next_action_unique") or "").strip() or "none"
guardian_level = str(guardian.get("level") or "unknown").strip().lower() or "unknown"
non_blocking_guardian_issues = {
    "dependency_policy_not_enforced",
    "architecture_ref_not_canonical",
    "missing_architecture_plan_ref",
    "missing_architecture_audit",
    "missing_vision_alignment",
}
blocking_issues = [item for item in issues if item not in non_blocking_guardian_issues]

try:
    state = json.loads(state_file.read_text(encoding="utf-8", errors="ignore"))
    if not isinstance(state, dict):
        state = {}
except Exception:
    state = {}

action = "skip"
reason = "no_actionable_work"
mode = "WAIT_RUNTIME"
message = ""
contract = None
prompt_mode = "default"

if active_subagent_ids:
    contract = active_strategy_task if active_strategy_task is not None else None
    mode = "COLLECT_ACTIVE_CAPABILITY"
    action = "kick"
    reason = "active_capability_requires_supervision"
    prompt_mode = "custom"
    message = (
        f"planner_companion relaunch: mode={mode} active_subagents={','.join(active_subagent_ids[:3])} "
        f"task_id={(contract['task_id'] if contract else 'none')} "
        f"next={(contract['suggested_next'] if contract else 'collect_or_repair')}."
    )
    if subagent_progress_age is not None and subagent_progress_age < active_stale_s and not issues:
        action = "skip"
        reason = f"active_capability_progress:{subagent_progress_age}s"
        message = ""
elif active_strategy_task is not None:
    contract = active_strategy_task
    mode = {
        "complete": "COMPLETE_OWNED_TASK",
        "run": "DISPATCH_CAPABILITY",
        "repair": "REPAIR_ORCHESTRATION",
    }.get(contract["suggested_next"], "COMPLETE_OWNED_TASK")
    action = "kick"
    reason = "resume_active_task"
    message = (
        f"planner_companion relaunch: mode={mode} task_id={contract['task_id']} "
        f"stream_id={contract['stream_id']} next={contract['suggested_next']} "
        f"target={contract['dispatch_target']} artifact={contract['artifact_path']}."
    )
    if contract_age is not None and contract_age < active_stale_s and not issues:
        action = "skip"
        reason = f"active_task_recent:{contract_age}s"
        message = ""
elif ready_planner_task is not None:
    contract = ready_planner_task
    mode = "CLAIM_PLANNER_TASK"
    action = "kick"
    reason = "planner_ready_needs_claim"
    if issues or dev_ready_count > 0:
        prompt_mode = "custom"
        message = (
            f"planner_companion relaunch: mode={mode} task_id={contract['task_id']} "
            f"stream_id={contract['stream_id']} ready_dev={dev_ready_count} next={next_action}."
        )
    if contract_age is not None and contract_age < idle_stale_s and not issues and dev_ready_count == 0:
        action = "skip"
        reason = f"idle_contract_recent:{contract_age}s"
        message = ""
elif dev_ready_count > 0:
    mode = "DISPATCH_CAPABILITY"
    action = "kick"
    reason = "dev_ready_requires_dispatch"
    prompt_mode = "custom"
    message = (
        f"planner_companion relaunch: mode={mode} dev_ready_count={dev_ready_count} "
        f"next={next_action}. Lancer la capability utile maintenant."
    )
elif issues:
    if guardian_level == "green" and not blocking_issues:
        mode = "WAIT_RUNTIME"
        action = "skip"
        reason = "guardian_green_nonblocking_issue"
        message = ""
    else:
        mode = "REPAIR_ORCHESTRATION"
        action = "kick"
        reason = "guardian_issue_requires_repair"
        prompt_mode = "custom"
        message = (
            f"planner_companion relaunch: mode={mode} guardian_level={guardian_level} "
            f"issues={','.join(issues[:4])} next={next_action}. "
            f"{recommendations[0] if recommendations else 'Corriger le blocker d orchestration courant.'}"
        )
elif guardian_age is not None and guardian_age > 7200 and contract_age is not None and contract_age > idle_stale_s:
    mode = "REPAIR_ORCHESTRATION"
    action = "kick"
    reason = "guardian_stale_recover_planner"

payload_fingerprint = hashlib.sha1(
    json.dumps(
        {
            "action": action,
            "reason": reason,
            "mode": mode,
            "contract": contract or {},
            "active_subagent_ids": active_subagent_ids[:4],
            "subagent_progress_age": subagent_progress_age,
            "dev_ready_count": dev_ready_count,
            "issues": issues[:4],
            "next_action": next_action,
        },
        sort_keys=True,
    ).encode("utf-8", errors="ignore")
).hexdigest()

last_kick_fp = str(state.get("last_kick_fp") or "").strip()
last_kick_at = int(state.get("last_kick_at") or 0)
if action == "kick" and payload_fingerprint == last_kick_fp and last_kick_at and (now - last_kick_at) < kick_cooldown_s:
    action = "skip"
    reason = f"kick_cooldown_active:{now - last_kick_at}s"
    message = ""

result = {
    "action": action,
    "reason": reason,
    "mode": mode,
    "message": message.strip(),
    "prompt_mode": "custom" if message.strip() else prompt_mode,
    "fingerprint": payload_fingerprint,
    "guardian_file": str(guardian_path) if guardian_path else "none",
    "workboard_file": str(board_path) if board_path else "none",
    "registry_file": str(registry_path) if registry_path else "none",
    "events_file": str(events_path) if events_path else "none",
    "guardian_level": guardian_level,
    "guardian_age_s": guardian_age if guardian_age is not None else -1,
    "contract_age_s": contract_age if contract_age is not None else -1,
    "subagent_progress_age_s": subagent_progress_age if subagent_progress_age is not None else -1,
    "active_subagents": ",".join(active_subagent_ids[:4]) if active_subagent_ids else "none",
    "active_task_id": contract["task_id"] if contract else "none",
    "stream_id": contract["stream_id"] if contract else "none",
    "suggested_next": contract["suggested_next"] if contract else "none",
    "dispatch_target": contract["dispatch_target"] if contract else "none",
    "ready_dev": dev_ready_count,
    "issues": ",".join(issues[:4]) if issues else "none",
    "next_action": next_action,
}
print(json.dumps(result, ensure_ascii=True))
PY
)"
rm -f "$BOARD_SNAPSHOT_FILE"

if [[ -z "$PAYLOAD" ]]; then
  echo "planner_companion_tick: empty payload" >&2
  exit 1
fi

ACTION="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("action","skip"))')"
REASON="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("reason","skip"))')"
MODE="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("mode","WAIT_RUNTIME"))')"
MESSAGE="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("message",""))')"
FINGERPRINT="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("fingerprint",""))')"
ACTIVE_TASK_ID="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("active_task_id","none"))')"
SUGGESTED_NEXT="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("suggested_next","none"))')"
PROMPT_MODE="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("prompt_mode","default"))')"

if [[ "$ACTION" == "skip" ]]; then
  python3 - "$STATE_FILE" "$FINGERPRINT" "$MODE" "$REASON" "$ACTIVE_TASK_ID" "$SUGGESTED_NEXT" <<'PY'
import json
import sys
import time
from pathlib import Path

state_file = Path(sys.argv[1])
state = {
    "last_seen_fp": sys.argv[2],
    "last_seen_at": int(time.time()),
    "last_action": "skip",
    "last_mode": sys.argv[3],
    "last_reason": sys.argv[4],
    "last_task_id": sys.argv[5],
    "last_suggested_next": sys.argv[6],
}
state_file.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
  echo "planner_companion_tick: skip ${REASON}"
  exit 0
fi

DIRECTIVE_POSTED=0
if [[ -n "$MESSAGE" ]]; then
  bash "$DIRECTIVE_BUS" post --targets planner --kind delivery --ttl-min 180 --msg "$MESSAGE" >/dev/null
  DIRECTIVE_POSTED=1
fi

nohup env \
  FC_PLANNER_COMPANION_TRIGGER=1 \
  FC_PLANNER_COMPANION_MODE="$MODE" \
  FC_PLANNER_COMPANION_REASON="$REASON" \
  FC_PLANNER_COMPANION_PROMPT_MODE="$PROMPT_MODE" \
  bash "${ROOT}/scripts/fc_agent_tick.sh" planner >>"$PLANNER_TICK_LOG" 2>&1 </dev/null &
LAUNCH_PID=$!

python3 - "$STATE_FILE" "$FINGERPRINT" "$MODE" "$REASON" "$ACTIVE_TASK_ID" "$SUGGESTED_NEXT" "$DIRECTIVE_POSTED" "$PROMPT_MODE" "$LAUNCH_PID" <<'PY'
import json
import sys
import time
from pathlib import Path

state_file = Path(sys.argv[1])
state = {
    "last_kick_fp": sys.argv[2],
    "last_kick_at": int(time.time()),
    "last_action": "kick",
    "last_mode": sys.argv[3],
    "last_reason": sys.argv[4],
    "last_task_id": sys.argv[5],
    "last_suggested_next": sys.argv[6],
    "last_directive_posted": int(sys.argv[7]),
    "last_prompt_mode": sys.argv[8],
    "last_launch_pid": int(sys.argv[9]),
}
state_file.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY

echo "planner_companion_tick: kicked planner mode=${MODE} reason=${REASON} task=${ACTIVE_TASK_ID} next=${SUGGESTED_NEXT} prompt_mode=${PROMPT_MODE} directive=${DIRECTIVE_POSTED} pid=${LAUNCH_PID}"
