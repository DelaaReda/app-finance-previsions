#!/usr/bin/env bash
# dependency_recompute.sh — periodic dependency/state refresh for queue/workboard
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ -f "$WORKSPACE_HELPER" ]]; then
  # shellcheck source=/dev/null
  source "$WORKSPACE_HELPER"
  ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
else
  ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
fi
cd "$ROOT"

ORCH_DIR="${ROOT}/logs-codex-runs/orchestrator-state"
QUEUE_FILE="${ORCH_DIR}/priority-queue.json"
WORKBOARD_FILE="${ORCH_DIR}/parallel-workstreams.json"

STALE_SWEEP_ENABLED="${FC_DEP_RECOMPUTE_STALE_SWEEP_ENABLED:-1}"
STALE_SWEEP_THRESHOLD_SECONDS="${FC_DEP_RECOMPUTE_STALE_SWEEP_THRESHOLD_SECONDS:-3600}"
STALE_SWEEP_ROLE="${FC_DEP_RECOMPUTE_STALE_SWEEP_ROLE:-all}"
DEP_REBUILD_ENABLED="${FC_DEP_REBUILD_FROM_VISION_ENABLED:-0}"
DEP_REBUILD_WAITING_DEP_THRESHOLD="${FC_DEP_REBUILD_WAITING_DEP_THRESHOLD:-10}"
DEP_REBUILD_READY_THRESHOLD="${FC_DEP_REBUILD_READY_THRESHOLD:-1}"
RECONCILE_ONLY="${FC_DEP_RECOMPUTE_RECONCILE_ONLY:-0}"
DIFF_FILE="${FC_DEP_RECOMPUTE_DIFF_FILE:-${ROOT}/logs-codex-runs/health/dependency-recompute-last-diff.json}"

snapshot_state_json() {
  python3 - <<'PY'
import json
import re
from pathlib import Path

root = Path(".").resolve()
pq_path = root / "logs-codex-runs" / "orchestrator-state" / "priority-queue.json"
wb_path = root / "logs-codex-runs" / "orchestrator-state" / "parallel-workstreams.json"

def jload(path: Path):
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
  except Exception:
    return {}

pq = jload(pq_path)
wb = jload(wb_path)
items = [i for i in pq.get("items", []) if isinstance(i, dict) and re.fullmatch(r"BATCH-\d{2}", str(i.get("id", "")).strip())]
tasks = [t for t in wb.get("tasks", []) if isinstance(t, dict)]

state_counts = {}
for s in ("READY", "IN_PROGRESS", "WAITING_DEP", "CLOSED", "PASS", "DONE", "PLANNED"):
  state_counts[s] = sum(1 for i in items if str(i.get("state", "")).upper() == s)

task_streams = {str(t.get("stream_id", "")).strip() for t in tasks if str(t.get("stream_id", "")).strip()}
queue_ids = {str(i.get("id", "")).strip() for i in items}
mismatch = sorted(task_streams - queue_ids)

payload = {
  "queue_file": str(pq_path),
  "workboard_file": str(wb_path),
  "queue_ready": state_counts["READY"],
  "queue_in_progress": state_counts["IN_PROGRESS"],
  "queue_waiting_dep": state_counts["WAITING_DEP"],
  "queue_planned": state_counts["PLANNED"],
  "workboard_ready": sum(1 for t in tasks if str(t.get("state", "")).upper() in {"READY", "READY_DEV", "READY_PLANNER"}),
  "workboard_in_progress": sum(1 for t in tasks if str(t.get("state", "")).upper() == "IN_PROGRESS"),
  "workboard_waiting_dep": sum(1 for t in tasks if str(t.get("state", "")).upper() == "WAITING_DEP"),
  "queue_ids_total": len(queue_ids),
  "workboard_streams_total": len(task_streams),
  "mismatch_count": len(mismatch),
  "mismatch_examples": mismatch[:20],
}
print(json.dumps(payload, ensure_ascii=True))
PY
}

BEFORE_SNAPSHOT="$(snapshot_state_json)"
rebuild_trigger="0"
stale_trigger="0"

python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --queue "$QUEUE_FILE" >/tmp/fc-dependency-recompute.out 2>&1 || {
  cat /tmp/fc-dependency-recompute.out >&2
  rm -f /tmp/fc-dependency-recompute.out
  exit 1
}

python3 - <<'PY'
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path(".").resolve()
wb_path = root / "logs-codex-runs" / "orchestrator-state" / "parallel-workstreams.json"

if not wb_path.exists():
    raise SystemExit(0)

board = json.loads(wb_path.read_text(encoding="utf-8", errors="ignore"))
tasks = [task for task in board.get("tasks", []) if isinstance(task, dict)]
now_text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def stream_id(task: dict) -> str:
    value = str(task.get("stream_id", "")).strip()
    if value:
        return value
    task_id = str(task.get("id", "")).strip()
    match = re.match(r"^(BATCH-\d+)", task_id)
    return match.group(1) if match else task_id

def delivery_delta(task: dict) -> str:
    value = str(task.get("last_delivery_delta", "")).strip().lower()
    return value if value and value not in {"none", "null"} else ""

changed = []
for source in tasks:
    if str(source.get("state", "")).strip().upper() != "IN_PROGRESS":
        continue
    delta = delivery_delta(source)
    if not delta:
        continue
    src_id = str(source.get("id", "")).strip()
    src_stream = stream_id(source)
    candidates = []
    for task in tasks:
        if str(task.get("state", "")).strip().upper() != "WAITING_DEP":
            continue
        if stream_id(task) != src_stream:
            continue
        deps = [str(dep).strip() for dep in task.get("depends_on", []) if str(dep).strip()]
        if src_id not in deps:
            continue
        other_ready = True
        for dep in deps:
            if dep == src_id:
                continue
            dep_task = next((item for item in tasks if str(item.get("id", "")).strip() == dep), None)
            dep_state = str((dep_task or {}).get("state", "")).strip().upper()
            if dep_state not in {"DONE", "CLOSED", "PASS"}:
                other_ready = False
                break
        if not other_ready:
            continue
        candidates.append(task)
    if not candidates:
        continue
    candidates.sort(key=lambda item: str(item.get("id", "")))
    target = candidates[0]
    target["state"] = "READY_DEV" if str(target.get("role", "")).strip().lower() == "dev" else "READY"
    target["blocked_reason"] = ""
    target["stalled_reason"] = ""
    target["updated_at"] = now_text
    target.setdefault("notes", []).append(
        f"delivery_unblocked:upstream={src_id};delta={delta};at={now_text}"
    )
    changed.append((src_id, str(target.get("id", "")).strip(), delta))

if changed:
    board["updated_at"] = now_text
    wb_path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        [
            "python3",
            "platform/automation/runtime/planner/planner_runtime_actions.py",
            "sync-priority",
            "--queue",
            str(root / "logs-codex-runs" / "orchestrator-state" / "priority-queue.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    for src_id, target_id, delta in changed:
        print(f"DELIVERY_CHAIN_UNBLOCK source={src_id} target={target_id} delta={delta}")
else:
    print("DELIVERY_CHAIN_UNBLOCK source=none target=none delta=none")
PY

read -r QUEUE_READY QUEUE_IN_PROGRESS QUEUE_WAITING_DEP WORKBOARD_READY WORKBOARD_IN_PROGRESS WORKBOARD_WAITING_DEP < <(python3 - <<'PY'
import json
import re
from pathlib import Path

root = Path(".").resolve()
pq_path = root / "logs-codex-runs" / "orchestrator-state" / "priority-queue.json"
wb_path = root / "logs-codex-runs" / "orchestrator-state" / "parallel-workstreams.json"

pq = json.loads(pq_path.read_text(encoding="utf-8", errors="ignore"))
wb = json.loads(wb_path.read_text(encoding="utf-8", errors="ignore"))

items = [i for i in pq.get("items", []) if re.fullmatch(r"BATCH-\d{2}", str(i.get("id", "")).strip())]
states = {}
for s in ("READY", "IN_PROGRESS", "WAITING_DEP", "CLOSED", "PASS", "DONE"):
    states[s] = sum(1 for i in items if str(i.get("state", "")).upper() == s)

tasks = wb.get("tasks", [])
wb_waiting = sum(1 for t in tasks if str(t.get("state", "")).upper() == "WAITING_DEP")
wb_ready = sum(1 for t in tasks if str(t.get("state", "")).upper() == "READY")
wb_ip = sum(1 for t in tasks if str(t.get("state", "")).upper() == "IN_PROGRESS")

print(
    f"{states['READY']} "
    f"{states['IN_PROGRESS']} "
    f"{states['WAITING_DEP']} "
    f"{wb_ready} "
    f"{wb_ip} "
    f"{wb_waiting}"
)
PY
)

if [[ "$RECONCILE_ONLY" == "1" ]]; then
  printf 'DEPENDENCY_RECOMPUTE_MODE reconcile_only=1 rebuild=disabled stale_sweep=disabled\n'
  printf 'DEPENDENCY_REBUILD_FROM_VISION trigger=0 reason=reconcile_only\n'
else
  if [[ "$DEP_REBUILD_ENABLED" == "1" ]] \
    && [[ "${QUEUE_WAITING_DEP:-0}" -ge "${DEP_REBUILD_WAITING_DEP_THRESHOLD:-10}" ]] \
    && [[ "${QUEUE_READY:-0}" -le "${DEP_REBUILD_READY_THRESHOLD:-1}" ]]; then
    rebuild_trigger="1"
    printf 'DEPENDENCY_REBUILD_FROM_VISION trigger=1 queue_ready=%s queue_waiting_dep=%s threshold_waiting_dep=%s threshold_ready=%s\n' \
      "${QUEUE_READY:-0}" "${QUEUE_WAITING_DEP:-0}" "${DEP_REBUILD_WAITING_DEP_THRESHOLD:-10}" "${DEP_REBUILD_READY_THRESHOLD:-1}"
    if ! bash scripts/rebuild_queue_from_product_vision.sh --apply >/tmp/fc-dependency-rebuild.out 2>&1; then
      cat /tmp/fc-dependency-rebuild.out >&2
      rm -f /tmp/fc-dependency-rebuild.out
      exit 1
    fi
    cat /tmp/fc-dependency-rebuild.out
    rm -f /tmp/fc-dependency-rebuild.out
    if ! python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --queue "$QUEUE_FILE" >/tmp/fc-dependency-recompute.out 2>&1; then
      cat /tmp/fc-dependency-recompute.out >&2
      rm -f /tmp/fc-dependency-recompute.out
      exit 1
    fi
  else
    printf 'DEPENDENCY_REBUILD_FROM_VISION trigger=0 queue_ready=%s queue_waiting_dep=%s threshold_waiting_dep=%s threshold_ready=%s\n' \
      "${QUEUE_READY:-0}" "${QUEUE_WAITING_DEP:-0}" "${DEP_REBUILD_WAITING_DEP_THRESHOLD:-10}" "${DEP_REBUILD_READY_THRESHOLD:-1}"
  fi

  if [[ "$STALE_SWEEP_ENABLED" == "1" ]] && [[ "${QUEUE_READY:-0}" -le 2 ]] && [[ "${QUEUE_WAITING_DEP:-0}" -ge 10 ]] && [[ "${WORKBOARD_IN_PROGRESS:-0}" -ge 1 ]]; then
    stale_trigger="1"
    STALE_CMD=(python3 platform/automation/workboard_stale_task_sweep.py --board "$WORKBOARD_FILE" --threshold-seconds "$STALE_SWEEP_THRESHOLD_SECONDS" --mode reclaim --apply)
    if [[ -n "${STALE_SWEEP_ROLE}" && "${STALE_SWEEP_ROLE}" != "all" ]]; then
      STALE_CMD+=(--role "$STALE_SWEEP_ROLE")
    fi
    printf 'DEPENDENCY_RECOMPUTE_STALE_SWEEP trigger=1 queue_ready=%s queue_waiting_dep=%s workboard_in_progress=%s threshold_s=%s role=%s\n' \
      "${QUEUE_READY:-0}" "${QUEUE_WAITING_DEP:-0}" "${WORKBOARD_IN_PROGRESS:-0}" "${STALE_SWEEP_THRESHOLD_SECONDS}" "${STALE_SWEEP_ROLE:-all}"
    if ! "${STALE_CMD[@]}" >/tmp/fc-stale-task-sweep.out 2>&1; then
      cat /tmp/fc-stale-task-sweep.out >&2
      rm -f /tmp/fc-stale-task-sweep.out
      exit 1
    fi
    cat /tmp/fc-stale-task-sweep.out
    rm -f /tmp/fc-stale-task-sweep.out
  else
    printf 'DEPENDENCY_RECOMPUTE_STALE_SWEEP trigger=0 queue_ready=%s queue_waiting_dep=%s workboard_in_progress=%s\n' \
      "${QUEUE_READY:-0}" "${QUEUE_WAITING_DEP:-0}" "${WORKBOARD_IN_PROGRESS:-0}"
  fi
fi

printf 'DEPENDENCY_RECOMPUTE_OK queue_ready=%s queue_in_progress=%s queue_waiting_dep=%s workboard_ready=%s workboard_in_progress=%s workboard_waiting_dep=%s\n' \
  "${QUEUE_READY:-0}" "${QUEUE_IN_PROGRESS:-0}" "${QUEUE_WAITING_DEP:-0}" "${WORKBOARD_READY:-0}" "${WORKBOARD_IN_PROGRESS:-0}" "${WORKBOARD_WAITING_DEP:-0}"

AFTER_SNAPSHOT="$(snapshot_state_json)"
mkdir -p "$(dirname "$DIFF_FILE")"
python3 - "$DIFF_FILE" "$BEFORE_SNAPSHOT" "$AFTER_SNAPSHOT" "$RECONCILE_ONLY" "$rebuild_trigger" "$stale_trigger" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

diff_file = Path(sys.argv[1])
before = json.loads(sys.argv[2])
after = json.loads(sys.argv[3])
reconcile_only = str(sys.argv[4] or "0").strip()
rebuild_trigger = str(sys.argv[5] or "0").strip()
stale_trigger = str(sys.argv[6] or "0").strip()

summary = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "mode": "reconcile_only" if reconcile_only == "1" else "default",
    "actions": {
        "sync_priority": True,
        "rebuild_from_vision_triggered": rebuild_trigger == "1",
        "stale_sweep_triggered": stale_trigger == "1",
    },
    "before": before,
    "after": after,
    "delta": {
        "queue_ready": int(after.get("queue_ready", 0)) - int(before.get("queue_ready", 0)),
        "queue_waiting_dep": int(after.get("queue_waiting_dep", 0)) - int(before.get("queue_waiting_dep", 0)),
        "workboard_ready": int(after.get("workboard_ready", 0)) - int(before.get("workboard_ready", 0)),
        "workboard_waiting_dep": int(after.get("workboard_waiting_dep", 0)) - int(before.get("workboard_waiting_dep", 0)),
        "mismatch_count": int(after.get("mismatch_count", 0)) - int(before.get("mismatch_count", 0)),
    },
}
diff_file.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(str(diff_file))
PY

cat /tmp/fc-dependency-recompute.out
rm -f /tmp/fc-dependency-recompute.out
printf 'DEPENDENCY_RECOMPUTE_DIFF file=%s mode=%s rebuild_trigger=%s stale_trigger=%s\n' \
  "$DIFF_FILE" "$([[ "$RECONCILE_ONLY" == "1" ]] && echo reconcile_only || echo default)" "$rebuild_trigger" "$stale_trigger"
