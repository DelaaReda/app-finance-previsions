#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || true)"
if [[ -z "$SCRIPT_PATH" ]]; then
  SCRIPT_PATH="$(python3 - "${BASH_SOURCE[0]}" <<'PY'
from pathlib import Path
import sys
print(str(Path(sys.argv[1]).resolve()))
PY
)"
fi
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "AUTO_DISPATCH status=ERROR reason=workspace_helper_missing path=$WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

DISPATCHER_ENABLED="${ADMIN_DISPATCHER_ENABLED:-${ADMIN_AGENTS_AUTO_DISPATCH_ENABLED:-1}}"
DISPATCHER_MODE="${ADMIN_DISPATCHER_MODE:-active}"
DISPATCHER_MAX_ACTIONS_PER_TICK="${ADMIN_DISPATCHER_MAX_ACTIONS_PER_TICK:-2}"
DISPATCHER_COOLDOWN_S="${ADMIN_DISPATCHER_COOLDOWN_S:-900}"
DISPATCHER_HANDOFF_STALE_S="${ADMIN_DISPATCHER_HANDOFF_STALE_S:-1200}"
DISPATCHER_READY_IDLE_THRESHOLD="${ADMIN_DISPATCHER_READY_IDLE_THRESHOLD:-1}"
DISPATCHER_SOFT_FAIL="${ADMIN_DISPATCHER_SOFT_FAIL:-1}"
DISPATCHER_SKIP_PREFLIGHT="${ADMIN_DISPATCHER_SKIP_PREFLIGHT:-0}"
DISPATCHER_SKIP_SYNC="${ADMIN_DISPATCHER_SKIP_SYNC:-0}"
DISPATCHER_TSHAPE_ENABLED="${ADMIN_DISPATCHER_TSHAPE_ENABLED:-1}"
DISPATCHER_TSHAPE_MODE="${ADMIN_DISPATCHER_TSHAPE_MODE:-full_takeover}"
DISPATCHER_TSHAPE_TRIGGER="${ADMIN_DISPATCHER_TSHAPE_TRIGGER:-first_blocked}"
DISPATCHER_TSHAPE_MAX_ACTIONS_PER_TICK="${ADMIN_DISPATCHER_TSHAPE_MAX_ACTIONS_PER_TICK:-3}"
DISPATCHER_TSHAPE_IGNORE_COOLDOWN="${ADMIN_DISPATCHER_TSHAPE_IGNORE_COOLDOWN:-1}"
DISPATCHER_TSHAPE_IGNORE_ROLE_TOUCH="${ADMIN_DISPATCHER_TSHAPE_IGNORE_ROLE_TOUCH:-1}"

STATE_DIR="${ADMIN_AGENTS_AUTO_DISPATCH_STATE_DIR:-$HOME/.openclaw/cron/admin-state}"
LOCK_FILE="$STATE_DIR/admin-agents-auto-dispatch.lock"
STATE_FILE="${ADMIN_DISPATCHER_STATE_FILE:-$STATE_DIR/admin-dispatcher-state.json}"
EVENTS_FILE="${ADMIN_DISPATCHER_EVENTS_FILE:-$ROOT/logs-codex-runs/admin-dispatcher/events.jsonl}"
QUEUE_FILE="${ADMIN_AGENTS_PRIORITY_QUEUE_FILE:-logs-codex-runs/orchestrator-state/priority-queue.json}"
BOARD_FILE="${ADMIN_AGENTS_WORKBOARD_FILE:-logs-codex-runs/orchestrator-state/parallel-workstreams.json}"

CHANGE_PLAN="${ADMIN_DISPATCHER_CHANGE_PLAN:-1 definir scope endpoint forecast ui; 2 verifier dependencies et impact upstream downstream; 3 analyser risk de regression forecast; 4 executer verification tests pytest snapshot; 5 preparer rollback fallback mitigation}"
ARCH_CHECKS="${ADMIN_DISPATCHER_ARCH_CHECKS:-forecast_contract; schema_stability; observability}"

mkdir -p "$STATE_DIR"
mkdir -p "$(dirname "$EVENTS_FILE")"

if [[ "$DISPATCHER_ENABLED" != "1" ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=dispatcher_disabled"
  exit 0
fi

if [[ "$DISPATCHER_MODE" != "active" ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=dispatcher_mode_${DISPATCHER_MODE}"
  exit 0
fi

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "AUTO_DISPATCH status=NOOP reason=locked"
    exit 0
  fi
fi

set +e
output="$(python3 - "$ROOT" "$QUEUE_FILE" "$BOARD_FILE" "$STATE_FILE" "$EVENTS_FILE" "$CHANGE_PLAN" "$ARCH_CHECKS" <<'PY'
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

root = Path(sys.argv[1])
queue_file = Path(sys.argv[2])
board_file = Path(sys.argv[3])
state_file = Path(sys.argv[4])
events_file = Path(sys.argv[5])
change_plan = sys.argv[6]
arch_checks = sys.argv[7]

ACTIVE_ROLES = ("planner", "dev", "admin")
ACTIVE_STATES = {"IN_PROGRESS", "REVIEW"}
READY_STATE = "READY"
ROLE_ORDER = {"planner": 0, "dev": 1, "admin": 2}
TEMPLATE_ORDER = {
    "PLAN": 0,
    "ANALYSIS": 1,
    "ARCH": 2,
    "DEV-01": 3,
    "DEV-02": 4,
    "DEV-03": 5,
    "ADMIN-01": 6,
    "GOV_REVIEW": 7,
}
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except Exception:
        return default
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def now_ts() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        if txt.endswith("Z"):
            txt = txt[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(txt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def epoch_seconds(value: Any) -> int:
    dt = parse_ts(value)
    if dt is None:
        return 0
    return int(dt.timestamp())


def normalize_role(value: Any) -> str:
    role = str(value or "").strip().lower()
    if role in {"backend_engineer", "frontend_engineer", "data_analyst", "integrator", "tester", "qa", "dev"}:
        return "dev"
    if role in {"clawsentinel", "infra_engineer", "admin"}:
        return "admin"
    if role in {"planner", "analyst", "architect", "po", "scrum_master", "vision-architect-tasks-planner", "vision_architect_tasks_planner"}:
        return "planner"
    return role


def batch_from_id(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    match = re.search(r"\b(BATCH-\d+)\b", text)
    return match.group(1) if match else None


def task_batch_id(task: Dict[str, Any]) -> Optional[str]:
    return batch_from_id(task.get("stream_id")) or batch_from_id(task.get("id"))


def task_code(task: Dict[str, Any], batch_id: str) -> str:
    code = str(task.get("code") or "").strip()
    if code:
        return code
    task_id = str(task.get("id") or "")
    prefix = f"{batch_id}-"
    if task_id.startswith(prefix):
        return task_id[len(prefix):]
    return task_id


def load_json_file(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def default_state() -> Dict[str, Any]:
    return {
        "version": 1,
        "last_run_at": 0,
        "ready_idle_streak": {role: 0 for role in ACTIVE_ROLES},
        "last_action_at": {role: 0 for role in ACTIVE_ROLES},
        "fairness_cursor": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "ready_wait_cycles": {},
        "takeover": {
            "active": False,
            "started_at": 0,
            "last_reason": "",
            "blocked_count": 0,
        },
    }


def load_state(path: Path) -> Dict[str, Any]:
    state = default_state()
    if not path.exists():
        return state
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return state
    if isinstance(loaded, dict):
        if isinstance(loaded.get("last_run_at"), (int, float)):
            state["last_run_at"] = int(loaded["last_run_at"])
        for key in ("ready_idle_streak", "last_action_at"):
            values = loaded.get(key)
            if isinstance(values, dict):
                for role in ACTIVE_ROLES:
                    raw = values.get(role)
                    if isinstance(raw, (int, float)):
                        state[key][role] = int(raw)
        fair = loaded.get("fairness_cursor")
        if isinstance(fair, dict):
            for label in ("P0", "P1", "P2", "P3"):
                raw = fair.get(label)
                if isinstance(raw, (int, float)):
                    state["fairness_cursor"][label] = max(0, int(raw))
        wait_cycles = loaded.get("ready_wait_cycles")
        if isinstance(wait_cycles, dict):
            for batch_id, raw in wait_cycles.items():
                bid = str(batch_id or "").strip()
                if not bid or not isinstance(raw, (int, float)):
                    continue
                state["ready_wait_cycles"][bid] = max(0, int(raw))
        takeover = loaded.get("takeover")
        if isinstance(takeover, dict):
            state["takeover"]["active"] = bool(takeover.get("active", False))
            for key in ("started_at", "blocked_count"):
                raw = takeover.get(key)
                if isinstance(raw, (int, float)):
                    state["takeover"][key] = int(raw)
            state["takeover"]["last_reason"] = str(takeover.get("last_reason") or "")
    return state


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    run = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
    return run.returncode, run.stdout.strip(), run.stderr.strip()


def append_event(event: Dict[str, Any]) -> None:
    events_file.parent.mkdir(parents=True, exist_ok=True)
    with events_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True) + "\n")


def event_base(
    *,
    event_name: str,
    tick_id: str,
    batch_id: str,
    task_id: str,
    target_role: str,
    reason_code: str,
    cooldown_hit: bool,
    result: str,
    queue_version: str,
    workboard_version: str,
    data_source: str,
) -> Dict[str, Any]:
    return {
        "ts_utc": now_ts().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event_name,
        "tick_id": tick_id,
        "batch_id": batch_id or "none",
        "task_id": task_id or "none",
        "target_role": target_role or "none",
        "reason_code": reason_code,
        "cooldown_hit": bool(cooldown_hit),
        "result": result,
        "queue_version": queue_version or "unknown",
        "workboard_version": workboard_version or "unknown",
        "data_source": data_source,
    }


def priority_value(item: Dict[str, Any]) -> int:
    return PRIORITY_RANK.get(str(item.get("priority") or "").strip().upper(), 9)


def sorted_ready_batches(queue_items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ready = [item for item in queue_items if str(item.get("state") or "").strip().upper() == READY_STATE]
    ready.sort(
        key=lambda item: (
            priority_value(item),
            epoch_seconds(item.get("created_at") or item.get("updated_at")),
            str(item.get("id") or ""),
        )
    )
    return ready


def ready_tasks(board: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [task for task in board.get("tasks", []) if str(task.get("state") or "").strip().upper() == READY_STATE]


def lane_busy_map(board: Dict[str, Any]) -> Dict[str, bool]:
    busy = {role: False for role in ACTIVE_ROLES}
    for task in board.get("tasks", []):
        state = str(task.get("state") or "").strip().upper()
        if state not in ACTIVE_STATES:
            continue
        role = normalize_role(task.get("assignee") or task.get("role"))
        if role in busy:
            busy[role] = True
    return busy


def batch_ready_tasks(board: Dict[str, Any], batch_id: str) -> List[Dict[str, Any]]:
    tasks = [task for task in ready_tasks(board) if task_batch_id(task) == batch_id]
    tasks.sort(
        key=lambda task: (
            TEMPLATE_ORDER.get(task_code(task, batch_id), 99),
            ROLE_ORDER.get(normalize_role(task.get("role")), 99),
            str(task.get("id") or ""),
        )
    )
    return tasks


def open_handoffs(board: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = [
        handoff
        for handoff in board.get("handoffs", [])
        if str(handoff.get("status") or "").strip().upper() == "OPEN"
    ]
    rows.sort(
        key=lambda row: epoch_seconds(row.get("updated_at") or row.get("created_at")),
        reverse=True,
    )
    return rows


def queue_order_map(queue_items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    rows = list(queue_items)
    rows.sort(
        key=lambda item: (
            priority_value(item),
            epoch_seconds(item.get("created_at") or item.get("updated_at")),
            str(item.get("id") or ""),
        )
    )
    out: Dict[str, int] = {}
    for idx, item in enumerate(rows):
        batch_id = str(item.get("id") or "")
        if batch_id and batch_id not in out:
            out[batch_id] = idx
    return out




def _priority_label(item: Dict[str, Any]) -> str:
    label = str(item.get("priority") or "").strip().upper()
    if label not in {"P0", "P1", "P2", "P3"}:
        label = "P3"
    return label


def update_ready_wait_cycles(state: Dict[str, Any], ready_batches: List[Dict[str, Any]]) -> Dict[str, int]:
    wait_cycles = state.setdefault("ready_wait_cycles", {})
    if not isinstance(wait_cycles, dict):
        wait_cycles = {}
        state["ready_wait_cycles"] = wait_cycles

    ready_ids = {str(item.get("id") or "") for item in ready_batches if str(item.get("id") or "")}
    for batch_id in list(wait_cycles.keys()):
        if batch_id not in ready_ids:
            wait_cycles.pop(batch_id, None)

    for batch_id in ready_ids:
        prev = wait_cycles.get(batch_id, 0)
        if not isinstance(prev, int):
            prev = 0
        wait_cycles[batch_id] = max(0, prev + 1)

    return wait_cycles


def fairness_order_ready_batches(
    ready_batches: List[Dict[str, Any]],
    state: Dict[str, Any],
    starve_cycles: int,
) -> Tuple[List[Dict[str, Any]], set[str]]:
    if not ready_batches:
        return [], set()

    queue_order = queue_order_map(ready_batches)
    wait_cycles = update_ready_wait_cycles(state, ready_batches)
    starved_ids = {batch_id for batch_id, cycles in wait_cycles.items() if int(cycles) >= starve_cycles}

    by_id = {str(item.get("id") or ""): item for item in ready_batches if str(item.get("id") or "")}
    ordered: List[Dict[str, Any]] = []
    used: set[str] = set()

    if starved_ids:
        for batch_id in sorted(
            starved_ids,
            key=lambda bid: (
                -int(wait_cycles.get(bid, 0)),
                priority_value(by_id.get(bid, {})),
                queue_order.get(bid, 99999),
                bid,
            ),
        ):
            item = by_id.get(batch_id)
            if item is None:
                continue
            ordered.append(item)
            used.add(batch_id)

    buckets: Dict[str, List[Dict[str, Any]]] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for item in ready_batches:
        batch_id = str(item.get("id") or "")
        if not batch_id or batch_id in used:
            continue
        buckets[_priority_label(item)].append(item)

    for label in buckets:
        buckets[label].sort(
            key=lambda item: (
                queue_order.get(str(item.get("id") or ""), 99999),
                str(item.get("id") or ""),
            )
        )

    fairness_cursor = state.setdefault("fairness_cursor", {"P0": 0, "P1": 0, "P2": 0, "P3": 0})
    for label in ("P0", "P1", "P2", "P3"):
        value = fairness_cursor.get(label, 0)
        if not isinstance(value, int) or value < 0:
            fairness_cursor[label] = 0

    weighted_sequence = ["P0", "P1", "P0", "P2", "P1", "P0", "P3", "P1", "P2", "P0"]
    while len(ordered) < len(ready_batches):
        progressed = False
        for label in weighted_sequence:
            bucket = buckets.get(label) or []
            if not bucket:
                continue
            idx = fairness_cursor[label] % len(bucket)
            chosen = bucket.pop(idx)
            fairness_cursor[label] = idx
            batch_id = str(chosen.get("id") or "")
            if not batch_id or batch_id in used:
                continue
            ordered.append(chosen)
            used.add(batch_id)
            progressed = True
            if len(ordered) >= len(ready_batches):
                break
        if not progressed:
            break

    if len(ordered) < len(ready_batches):
        for item in ready_batches:
            batch_id = str(item.get("id") or "")
            if batch_id and batch_id not in used:
                ordered.append(item)
                used.add(batch_id)

    return ordered, starved_ids

def blocked_signals(queue: Dict[str, Any], board: Dict[str, Any]) -> Dict[str, int]:
    tasks = board.get("tasks", [])
    streams = board.get("streams", [])
    queue_items = queue.get("items", [])
    task_blocked = sum(1 for task in tasks if str(task.get("state") or "").strip().upper() == "BLOCKED")
    stream_blocked = sum(1 for stream in streams if str(stream.get("state") or "").strip().upper() == "BLOCKED")
    queue_blocked = sum(1 for item in queue_items if str(item.get("state") or "").strip().upper() == "BLOCKED")
    return {
        "task_blocked": task_blocked,
        "stream_blocked": stream_blocked,
        "queue_blocked": queue_blocked,
        "total": task_blocked + stream_blocked + queue_blocked,
    }


def bool_result(status: bool, ok_code: str, fail_code: str) -> str:
    return ok_code if status else fail_code


max_actions = env_int("ADMIN_DISPATCHER_MAX_ACTIONS_PER_TICK", 2, 1, 5)
cooldown_s = env_int("ADMIN_DISPATCHER_COOLDOWN_S", 900, 0, 86400)
handoff_stale_s = env_int("ADMIN_DISPATCHER_HANDOFF_STALE_S", 1200, 0, 86400)
ready_idle_threshold = env_int("ADMIN_DISPATCHER_READY_IDLE_THRESHOLD", 1, 0, 10)
fairness_starve_cycles = env_int("ADMIN_DISPATCHER_FAIRNESS_MAX_STARVE_CYCLES", 3, 1, 50)
soft_fail = env_bool("ADMIN_DISPATCHER_SOFT_FAIL", True)
skip_preflight = env_bool("ADMIN_DISPATCHER_SKIP_PREFLIGHT", False)
skip_sync = env_bool("ADMIN_DISPATCHER_SKIP_SYNC", False)

if not queue_file.exists():
    print("AUTO_DISPATCH status=NOOP reason=queue_missing")
    raise SystemExit(0)
if not board_file.exists():
    print("AUTO_DISPATCH status=NOOP reason=board_missing")
    raise SystemExit(0)

state = load_state(state_file)
state["last_run_at"] = int(now_ts().timestamp())

tick_id = f"admin_dispatch_{int(now_ts().timestamp())}"

if not skip_sync:
    rc, _out, err = run_cmd(
        [
            sys.executable,
            "platform/automation/compat/projections/parallel_workstream.py",
            "--board",
            str(board_file),
            "sync-priority",
            "--include-pass",
        ]
    )
    if rc != 0:
        queue_data = load_json_file(queue_file)
        board_data = load_json_file(board_file)
        queue_version = str(queue_data.get("version") or "unknown")
        workboard_version = str(board_data.get("version") or "unknown")
        append_event(
            event_base(
                event_name="dispatch_result",
                tick_id=tick_id,
                batch_id="none",
                task_id="none",
                target_role="admin",
                reason_code="NO_ACTIONABLE_READY",
                cooldown_hit=False,
                result="blocked_soft",
                queue_version=queue_version,
                workboard_version=workboard_version,
                data_source=f"{queue_file}:{board_file}",
            )
            | {"error": f"sync_failed_rc_{rc}", "stderr": err[:240]}
        )
        save_state(state_file, state)
        if soft_fail:
            print("AUTO_DISPATCH status=WARN reason=sync_failed")
            raise SystemExit(0)
        print("AUTO_DISPATCH status=ERROR reason=sync_failed")
        raise SystemExit(2)

queue_data = load_json_file(queue_file)
board_data = load_json_file(board_file)
queue_version = str(queue_data.get("version") or "unknown")
workboard_version = str(board_data.get("version") or "unknown")
data_source = f"{queue_file}:{board_file}"

lane_busy = lane_busy_map(board_data)
initial_lane_busy = dict(lane_busy)
ready_task_rows = ready_tasks(board_data)

# Update ready idle streaks for active roles.
for role in ACTIVE_ROLES:
    has_ready = any(normalize_role(task.get("role") or task.get("assignee")) == role for task in ready_task_rows)
    if has_ready and not initial_lane_busy.get(role, False):
        state["ready_idle_streak"][role] = int(state["ready_idle_streak"].get(role, 0)) + 1
    else:
        state["ready_idle_streak"][role] = 0

ready_batches = sorted_ready_batches(queue_data.get("items", []))
ordered_ready_batches, starved_batch_ids = fairness_order_ready_batches(
    ready_batches,
    state,
    fairness_starve_cycles,
)
selected_batch = ordered_ready_batches[0] if ordered_ready_batches else None
selected_batch_id = str(selected_batch.get("id") or "") if selected_batch else ""

candidates: List[Dict[str, Any]] = []
candidate_by_task: Dict[str, Dict[str, Any]] = {}

def register_candidate(candidate: Dict[str, Any]) -> None:
    task_id = candidate.get("task_id")
    if not task_id:
        return
    existing = candidate_by_task.get(task_id)
    if existing is None:
        candidate_by_task[task_id] = candidate
        return
    new_key = (
        int(candidate.get("rank", 9)),
        int(candidate.get("stream_fairness_slot", 9999)),
        int(candidate.get("order", 9999)),
    )
    cur_key = (
        int(existing.get("rank", 9)),
        int(existing.get("stream_fairness_slot", 9999)),
        int(existing.get("order", 9999)),
    )
    if new_key < cur_key:
        candidate_by_task[task_id] = candidate

# 1) Open handoff stale recovery path.
for handoff in open_handoffs(board_data):
    target_role = normalize_role(handoff.get("to_role") or handoff.get("handoff_to") or handoff.get("target_role"))
    if target_role not in ACTIVE_ROLES:
        continue
    if lane_busy.get(target_role, False):
        continue
    handoff_ts = epoch_seconds(handoff.get("updated_at") or handoff.get("created_at"))
    if handoff_ts <= 0:
        continue
    age_s = int(now_ts().timestamp()) - handoff_ts
    if age_s < handoff_stale_s:
        continue
    batch_id = batch_from_id(handoff.get("from_task") or handoff.get("task_id") or handoff.get("id"))
    if not batch_id:
        continue
    for task in batch_ready_tasks(board_data, batch_id):
        role = normalize_role(task.get("role") or task.get("assignee"))
        if role != target_role:
            continue
        register_candidate(
            {
                "rank": 0,
                "batch_id": batch_id,
                "task_id": str(task.get("id") or ""),
                "target_role": target_role,
                "reason_code": "OPEN_HANDOFF_STALE",
                "dispatch_reason_code": "OPEN_HANDOFF_STALE",
                "stream_fairness_slot": 0,
                "handoff_age_s": age_s,
                "order": len(candidate_by_task) + 1,
            }
        )
        break

# 2) READY batch path with weighted local-DAG fairness.
for fairness_slot, ready_batch in enumerate(ordered_ready_batches, start=1):
    batch_id = str(ready_batch.get("id") or "")
    if not batch_id:
        continue
    for task in batch_ready_tasks(board_data, batch_id):
        role = normalize_role(task.get("role") or task.get("assignee"))
        if role not in ACTIVE_ROLES:
            continue
        if lane_busy.get(role, False):
            continue
        streak = int(state["ready_idle_streak"].get(role, 0))
        reason = "LANE_IDLE_WITH_READY" if streak >= ready_idle_threshold else "READY_ITEM_AVAILABLE"
        if batch_id in starved_batch_ids:
            reason = "FAIRNESS_STARVATION_RELIEF"
        register_candidate(
            {
                "rank": 1,
                "batch_id": batch_id,
                "task_id": str(task.get("id") or ""),
                "target_role": role,
                "reason_code": reason,
                "dispatch_reason_code": reason,
                "stream_fairness_slot": fairness_slot,
                "handoff_age_s": 0,
                "order": len(candidate_by_task) + 1,
            }
        )
        break

candidates = sorted(
    candidate_by_task.values(),
    key=lambda row: (
        int(row.get("rank", 9)),
        int(row.get("stream_fairness_slot", 9999)),
        ROLE_ORDER.get(str(row.get("target_role") or ""), 99),
        int(row.get("order", 0)),
        str(row.get("task_id") or ""),
    ),
)

# Decision trace (pre-action).
for candidate in candidates:
    append_event(
        event_base(
            event_name="dispatch_decision",
            tick_id=tick_id,
            batch_id=str(candidate.get("batch_id") or "none"),
            task_id=str(candidate.get("task_id") or "none"),
            target_role=str(candidate.get("target_role") or "none"),
            reason_code=str(candidate.get("reason_code") or "NO_ACTIONABLE_READY"),
            cooldown_hit=False,
            result="noop",
            queue_version=queue_version,
            workboard_version=workboard_version,
            data_source=data_source,
        )
        | {
            "dispatch_reason_code": str(candidate.get("dispatch_reason_code") or candidate.get("reason_code") or "NO_ACTIONABLE_READY"),
            "stream_fairness_slot": int(candidate.get("stream_fairness_slot") or 0),
        }
    )

actions = 0
claims_ok = 0
claims_failed = 0
cooldown_hits = 0
first_success_reason = ""
first_success_slot = 0
touched_roles: set[str] = set()

for candidate in candidates:
    if actions >= max_actions:
        break

    role = str(candidate.get("target_role") or "")
    task_id = str(candidate.get("task_id") or "")
    batch_id = str(candidate.get("batch_id") or "none")
    reason_code = str(candidate.get("reason_code") or "READY_ITEM_AVAILABLE")

    last_action_at = int(state["last_action_at"].get(role, 0))
    now_epoch = int(now_ts().timestamp())
    if role in touched_roles or (cooldown_s > 0 and (now_epoch - last_action_at) < cooldown_s):
        cooldown_hits += 1
        append_event(
            event_base(
                event_name="dispatch_result",
                tick_id=tick_id,
                batch_id=batch_id,
                task_id=task_id,
                target_role=role,
                reason_code="COOLDOWN_ACTIVE",
                cooldown_hit=True,
                result="noop",
                queue_version=queue_version,
                workboard_version=workboard_version,
                data_source=data_source,
            )
            | {
                "dispatch_reason_code": "COOLDOWN_ACTIVE",
                "stream_fairness_slot": int(candidate.get("stream_fairness_slot") or 0),
            }
        )
        continue

    append_event(
        event_base(
            event_name="dispatch_action",
            tick_id=tick_id,
            batch_id=batch_id,
            task_id=task_id,
            target_role=role,
            reason_code=reason_code,
            cooldown_hit=False,
            result="noop",
            queue_version=queue_version,
            workboard_version=workboard_version,
            data_source=data_source,
        )
        | {
            "dispatch_reason_code": str(candidate.get("dispatch_reason_code") or reason_code),
            "stream_fairness_slot": int(candidate.get("stream_fairness_slot") or 0),
        }
    )

    rc, out, err = run_cmd(
        [
            sys.executable,
            "platform/automation/compat/projections/parallel_workstream.py",
            "--board",
            str(board_file),
            "claim",
            "--role",
            role,
            "--task",
            task_id,
            "--change-plan",
            change_plan,
            "--architecture-checks",
            arch_checks,
        ]
    )

    actions += 1
    if rc == 0:
        claims_ok += 1
        touched_roles.add(role)
        state["last_action_at"][role] = now_epoch
        lane_busy[role] = True
        wait_cycles = state.setdefault("ready_wait_cycles", {})
        if isinstance(wait_cycles, dict) and batch_id:
            wait_cycles[batch_id] = 0
        if not first_success_reason:
            first_success_reason = str(candidate.get("dispatch_reason_code") or reason_code)
            first_success_slot = int(candidate.get("stream_fairness_slot") or 0)
        append_event(
            event_base(
                event_name="dispatch_result",
                tick_id=tick_id,
                batch_id=batch_id,
                task_id=task_id,
                target_role=role,
                reason_code=reason_code,
                cooldown_hit=False,
                result="ok",
                queue_version=queue_version,
                workboard_version=workboard_version,
                data_source=data_source,
            )
            | {"stdout": out[:240], "dispatch_reason_code": str(candidate.get("dispatch_reason_code") or reason_code), "stream_fairness_slot": int(candidate.get("stream_fairness_slot") or 0)}
        )
    else:
        claims_failed += 1
        append_event(
            event_base(
                event_name="dispatch_result",
                tick_id=tick_id,
                batch_id=batch_id,
                task_id=task_id,
                target_role=role,
                reason_code="CLAIM_FAILED_SOFT",
                cooldown_hit=False,
                result="blocked_soft" if soft_fail else "warn",
                queue_version=queue_version,
                workboard_version=workboard_version,
                data_source=data_source,
            )
            | {"stderr": err[:240], "rc": rc, "dispatch_reason_code": str(candidate.get("dispatch_reason_code") or reason_code), "stream_fairness_slot": int(candidate.get("stream_fairness_slot") or 0)}
        )

if not candidates:
    append_event(
        event_base(
            event_name="dispatch_result",
            tick_id=tick_id,
            batch_id=selected_batch_id or "none",
            task_id="none",
            target_role="none",
            reason_code="NO_ACTIONABLE_READY",
            cooldown_hit=False,
            result="noop",
            queue_version=queue_version,
            workboard_version=workboard_version,
            data_source=data_source,
        )
        | {"dispatch_reason_code": "NO_ACTIONABLE_READY", "stream_fairness_slot": 0}
    )

save_state(state_file, state)

if claims_ok > 0:
    status = "OK"
    top_reason = first_success_reason or "READY_ITEM_AVAILABLE"
elif claims_failed > 0:
    status = "WARN"
    top_reason = "CLAIM_FAILED_SOFT"
elif cooldown_hits > 0:
    status = "NOOP"
    top_reason = "COOLDOWN_ACTIVE"
elif candidates:
    status = "NOOP"
    top_reason = str(candidates[0].get("dispatch_reason_code") or "READY_ITEM_AVAILABLE")
else:
    status = "NOOP"
    top_reason = "NO_ACTIONABLE_READY"

print(
    "AUTO_DISPATCH "
    f"status={status} "
    f"mode=active "
    f"ready_batch={selected_batch_id or 'none'} "
    f"decisions={len(candidates)} "
    f"actions={actions} "
    f"ok={claims_ok} "
    f"failed={claims_failed} "
    f"cooldown={cooldown_hits} "
    f"reason={top_reason} "
    f"fairness_slot={first_success_slot if claims_ok > 0 else 0}"
)

if claims_failed > 0 and not soft_fail:
    raise SystemExit(2)

raise SystemExit(0)
PY
)"; rc=$?
set -e

if [[ "$rc" -eq 0 ]]; then
  echo "$output"
  exit 0
fi

if [[ "$DISPATCHER_SOFT_FAIL" == "1" ]]; then
  echo "AUTO_DISPATCH status=WARN reason=dispatcher_engine_failed rc=$rc detail=$(printf '%s' \"$output\" | tr '\n' '|' | sed 's/|*$//')"
  exit 0
fi

echo "AUTO_DISPATCH status=ERROR reason=dispatcher_engine_failed rc=$rc detail=$(printf '%s' \"$output\" | tr '\n' '|' | sed 's/|*$//')" >&2
exit "$rc"
