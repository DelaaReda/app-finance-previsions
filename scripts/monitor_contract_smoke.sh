#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
TIMEOUT_SECONDS="${FC_MONITOR_SMOKE_TIMEOUT_SECONDS:-8}"
QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-$BASE_URL}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-$TIMEOUT_SECONDS}"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: bash scripts/monitor_contract_smoke.sh [--base-url URL] [--timeout SEC] [--quiet]" >&2
      exit 2
      ;;
  esac
done

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "Invalid timeout: $TIMEOUT_SECONDS" >&2
  exit 2
fi

STATUS_JSON="$(curl -fsS --max-time "$TIMEOUT_SECONDS" "${BASE_URL%/}/api/status")"
DIAG_JSON="$(curl -fsS --max-time "$TIMEOUT_SECONDS" "${BASE_URL%/}/api/runtime-diagnostics")"
ISSUES_FEED_JSON="$(curl -fsS --max-time "$TIMEOUT_SECONDS" "${BASE_URL%/}/api/issues/feed?n=40&window_min=120")"
ISSUES_SUMMARY_JSON="$(curl -fsS --max-time "$TIMEOUT_SECONDS" "${BASE_URL%/}/api/issues/summary?window_min=60")"

SUMMARY="$(
python3 - "$STATUS_JSON" "$DIAG_JSON" "$ISSUES_FEED_JSON" "$ISSUES_SUMMARY_JSON" <<'PY'
import json
import sys

status_raw, diag_raw, issues_feed_raw, issues_summary_raw = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
errors = []

def ensure(cond, msg):
    if not cond:
        errors.append(msg)

try:
    status = json.loads(status_raw)
except Exception as exc:
    print(f"invalid_status_json:{exc}")
    sys.exit(1)

try:
    diag = json.loads(diag_raw)
except Exception as exc:
    print(f"invalid_runtime_diagnostics_json:{exc}")
    sys.exit(1)

try:
    issues_feed = json.loads(issues_feed_raw)
except Exception as exc:
    print(f"invalid_issues_feed_json:{exc}")
    sys.exit(1)

try:
    issues_summary = json.loads(issues_summary_raw)
except Exception as exc:
    print(f"invalid_issues_summary_json:{exc}")
    sys.exit(1)

ensure(isinstance(status, dict), "status_not_object")
ensure(isinstance(diag, dict), "runtime_diagnostics_not_object")
ensure(isinstance(issues_feed, dict), "issues_feed_not_object")
ensure(isinstance(issues_summary, dict), "issues_summary_not_object")

required_status = ("health", "roles", "queue", "workboard", "agents", "data_freshness_s", "data_source")
for key in required_status:
    ensure(key in status, f"status_missing_{key}")
for key in ("issues_recent_by_role", "critical_open_count", "issue_publication_gap_roles"):
    ensure(key in status, f"status_missing_{key}")

health = status.get("health")
ensure(isinstance(health, str), "status_health_not_string")

roles = status.get("roles")
ensure(isinstance(roles, list), "status_roles_not_list")
if isinstance(roles, list):
    ensure(len(roles) > 0, "status_roles_empty")

agents = status.get("agents")
ensure(isinstance(agents, dict), "status_agents_not_object")
core_roles = ("planner", "dev", "admin")
if isinstance(agents, dict):
    for role in core_roles:
        ensure(role in agents, f"status_agents_missing_{role}")
        entry = agents.get(role, {})
        ensure(isinstance(entry, dict), f"status_agents_{role}_not_object")
        if isinstance(entry, dict):
            for field in ("status", "verdict", "blocker", "tick_age_min", "source"):
                ensure(field in entry, f"status_agents_{role}_missing_{field}")

ensure(isinstance(status.get("data_freshness_s"), int), "status_data_freshness_not_int")
ensure(isinstance(status.get("data_source"), str), "status_data_source_not_string")

queue = status.get("queue")
ensure(isinstance(queue, dict), "status_queue_not_object")
if isinstance(queue, dict):
    ensure("state_counts" in queue and isinstance(queue.get("state_counts"), dict), "queue_state_counts_invalid")

workboard = status.get("workboard")
ensure(isinstance(workboard, dict), "status_workboard_not_object")
if isinstance(workboard, dict):
    for key in ("ready", "in_progress", "done"):
        ensure(key in workboard, f"workboard_missing_{key}")

required_diag = ("generated_at", "signals", "agents", "data_freshness_s", "data_source")
for key in required_diag:
    ensure(key in diag, f"runtime_diagnostics_missing_{key}")

diag_agents = diag.get("agents")
ensure(isinstance(diag_agents, dict), "runtime_diagnostics_agents_not_object")
if isinstance(diag_agents, dict):
    for role in core_roles:
        ensure(role in diag_agents, f"runtime_diagnostics_agents_missing_{role}")
        entry = diag_agents.get(role, {})
        ensure(isinstance(entry, dict), f"runtime_diagnostics_agents_{role}_not_object")

ensure(isinstance(diag.get("data_freshness_s"), int), "runtime_diagnostics_data_freshness_not_int")
ensure(isinstance(diag.get("data_source"), str), "runtime_diagnostics_data_source_not_string")

signals = diag.get("signals")
ensure(isinstance(signals, dict), "runtime_diagnostics_signals_not_object")
if isinstance(signals, dict):
    required_signals = (
        "permission_errors_recent",
        "health_degraded_recent",
        "health_stale_recent",
        "admin_timeout_events_recent",
        "planner_guard_blocked",
        "planner_blocker_id",
    )
    for key in required_signals:
        ensure(key in signals, f"signals_missing_{key}")

required_issues_feed = ("count", "items", "filters", "source")
for key in required_issues_feed:
    ensure(key in issues_feed, f"issues_feed_missing_{key}")
ensure(isinstance(issues_feed.get("items"), list), "issues_feed_items_not_list")

required_issues_summary = (
    "window_min",
    "total_records",
    "totals_by_severity",
    "top_codes",
    "roles_touched",
    "mttr_estimated_by_role",
    "issues_recent_by_role",
    "critical_open_count",
    "issue_publication_gap_roles",
)
for key in required_issues_summary:
    ensure(key in issues_summary, f"issues_summary_missing_{key}")
ensure(isinstance(issues_summary.get("totals_by_severity"), dict), "issues_summary_totals_not_object")
ensure(isinstance(issues_summary.get("top_codes"), list), "issues_summary_top_codes_not_list")

if errors:
    print("FAIL " + ",".join(errors))
    sys.exit(1)

print(
    "PASS "
    f"health={health} "
    f"roles={len(roles) if isinstance(roles, list) else 0} "
    f"agents={len(agents) if isinstance(agents, dict) else 0} "
    f"queue_states={len(queue.get('state_counts', {})) if isinstance(queue, dict) else 0} "
    f"workboard_ready={workboard.get('ready') if isinstance(workboard, dict) else 'na'} "
    f"admin_timeouts_recent={signals.get('admin_timeout_events_recent') if isinstance(signals, dict) else 'na'} "
    f"issues_records={issues_summary.get('total_records') if isinstance(issues_summary, dict) else 'na'}"
)
PY
)"

if [[ "$QUIET" -eq 0 ]]; then
  echo "$SUMMARY"
fi

if [[ "$SUMMARY" != PASS* ]]; then
  exit 1
fi
