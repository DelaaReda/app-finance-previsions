#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

BOARD_FILE="${KPI_BOARD_FILE:-logs-codex-runs/orchestrator-state/parallel-workstreams.json}"
QUEUE_FILE="${KPI_QUEUE_FILE:-logs-codex-runs/orchestrator-state/priority-queue.json}"
OUT_FILE="${KPI_OUT_FILE:-logs-codex-runs/orchestrator-state/kpi-history.jsonl}"
ACK_SLA_SECONDS="${KPI_ACK_SLA_SECONDS:-900}"
CLOSE_SLA_SECONDS="${KPI_CLOSE_SLA_SECONDS:-3600}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: export_orchestration_kpi.sh [options]

Options:
  --board <path>          Workboard JSON path
  --queue <path>          Priority queue JSON path
  --out <path>            KPI JSONL output path
  --ack-sla-seconds <n>   Handoff ACK SLA (default: 900)
  --close-sla-seconds <n> Handoff CLOSE SLA (default: 3600)
  --dry-run               Print KPI line without writing file
  -h, --help              Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --board) BOARD_FILE="${2:-}"; shift 2 ;;
    --queue) QUEUE_FILE="${2:-}"; shift 2 ;;
    --out) OUT_FILE="${2:-}"; shift 2 ;;
    --ack-sla-seconds) ACK_SLA_SECONDS="${2:-}"; shift 2 ;;
    --close-sla-seconds) CLOSE_SLA_SECONDS="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! [[ "$ACK_SLA_SECONDS" =~ ^[0-9]+$ ]] || [[ "$ACK_SLA_SECONDS" -lt 1 ]]; then
  ACK_SLA_SECONDS=900
fi
if ! [[ "$CLOSE_SLA_SECONDS" =~ ^[0-9]+$ ]] || [[ "$CLOSE_SLA_SECONDS" -lt 1 ]]; then
  CLOSE_SLA_SECONDS=3600
fi

if [[ ! -f "$BOARD_FILE" ]]; then
  echo "KPI_EXPORT status=BLOCKED reason=board_missing board=$BOARD_FILE"
  exit 3
fi

kpi_line="$(python3 - "$BOARD_FILE" "$QUEUE_FILE" "$ACK_SLA_SECONDS" "$CLOSE_SLA_SECONDS" <<'PY'
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

board_path = Path(sys.argv[1])
queue_path = Path(sys.argv[2])
ack_sla = int(sys.argv[3])
close_sla = int(sys.argv[4])

def parse_utc(text: str):
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

board = json.loads(board_path.read_text(encoding="utf-8"))
queue = {}
if queue_path.exists():
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        queue = {}

now = datetime.now(timezone.utc)
window_start = now - timedelta(hours=24)
tasks = board.get("tasks", [])
handoffs = board.get("handoffs", [])

done_tasks = [t for t in tasks if str(t.get("state", "")) == "DONE"]
done_total = len(done_tasks)
done_24h = 0
done_with_manifest = 0
done_with_cmd_tests = 0
for task in done_tasks:
    completed_at = parse_utc(str(task.get("completed_at", "")))
    if completed_at and completed_at >= window_start:
        done_24h += 1
    manifests = [m for m in task.get("proof_manifests", []) if str(m).strip()]
    if manifests:
        done_with_manifest += 1
    notes_blob = " ".join(str(n) for n in task.get("notes", [])).upper()
    if "CMD=" in notes_blob and "TESTS_RUN=" in notes_blob:
        done_with_cmd_tests += 1

open_handoffs = 0
ack_overdue = 0
close_overdue = 0
for handoff in handoffs:
    status = str(handoff.get("status", "")).upper()
    if status not in {"OPEN", "ACK"}:
        continue
    created_at = parse_utc(str(handoff.get("created_at", ""))) or parse_utc(str(handoff.get("updated_at", "")))
    if created_at is None:
        continue
    age = int((now - created_at).total_seconds())
    if status == "OPEN":
        open_handoffs += 1
        if age > ack_sla:
            ack_overdue += 1
        if age > close_sla:
            close_overdue += 1
    elif status == "ACK":
        ack_at = parse_utc(str(handoff.get("updated_at", ""))) or created_at
        age_ack = int((now - ack_at).total_seconds())
        if age_ack > close_sla:
            close_overdue += 1

items = queue.get("items", []) if isinstance(queue, dict) else []
queue_ready = sum(1 for item in items if str(item.get("state", "")).upper() == "READY")
queue_pass = sum(1 for item in items if str(item.get("state", "")).upper() == "PASS")

evidence_completeness = 1.0
if done_total > 0:
    evidence_completeness = round(done_with_manifest / done_total, 4)

kpi = {
    "ts_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "done_total": done_total,
    "done_24h": done_24h,
    "done_with_manifest": done_with_manifest,
    "done_with_cmd_tests": done_with_cmd_tests,
    "evidence_completeness": evidence_completeness,
    "open_handoffs": open_handoffs,
    "handoff_ack_overdue": ack_overdue,
    "handoff_close_overdue": close_overdue,
    "queue_ready": queue_ready,
    "queue_pass": queue_pass,
}
print(json.dumps(kpi, ensure_ascii=True, separators=(",", ":")))
PY
)"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "$kpi_line"
  echo "KPI_EXPORT status=PASS dry_run=1 out=$OUT_FILE"
  exit 0
fi

mkdir -p "$(dirname "$OUT_FILE")"
printf '%s\n' "$kpi_line" >> "$OUT_FILE"
echo "KPI_EXPORT status=PASS dry_run=0 out=$OUT_FILE"
