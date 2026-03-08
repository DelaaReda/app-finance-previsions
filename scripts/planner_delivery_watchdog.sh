#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
LOG_DIR="$ROOT/logs-codex-runs/ops"
LOG_FILE="$LOG_DIR/planner-delivery-watchdog.log"
PID_FILE="/tmp/planner-delivery-watchdog.pid"
INTERVAL_SECONDS=120
DURATION_SECONDS=3600

while [ $# -gt 0 ]; do
  case "$1" in
    --interval)
      INTERVAL_SECONDS="${2:-120}"
      shift 2
      ;;
    --duration)
      DURATION_SECONDS="${2:-3600}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "$(date -Is) watchdog_already_running pid=$old_pid" >>"$LOG_FILE"
    exit 0
  fi
fi

echo $$ >"$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

cd "$ROOT"
bash scripts/runtime_host_check.sh >/dev/null

end_ts=$(( $(date +%s) + DURATION_SECONDS ))

log() {
  printf '%s %s\n' "$(date -Is)" "$*" >>"$LOG_FILE"
}

cleanup_orphan_capabilities() {
  python3 - <<'PY'
import json, pathlib, subprocess

root = pathlib.Path("/home/venom/analyse-financiere")
registry_path = root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
try:
    obj = json.loads(registry_path.read_text())
except Exception:
    obj = {}
subagents = obj.get("subagents") if isinstance(obj, dict) else obj
subagents = subagents if isinstance(subagents, list) else []
keep = {row.get("subagent_id") for row in subagents if isinstance(row, dict) and row.get("subagent_id")}
try:
    agents = json.loads(subprocess.check_output(["openclaw", "agents", "list", "--json"], text=True))
except Exception:
    print("cleanup_removed=0")
    raise SystemExit(0)
remove = []
for item in agents if isinstance(agents, list) else []:
    if not isinstance(item, dict):
        continue
    agent_id = str(item.get("id") or "").strip()
    if (agent_id.startswith("planner_dev_") or agent_id.startswith("planner_admin_")) and agent_id not in keep:
        remove.append(agent_id)
for agent_id in sorted(set(remove)):
    subprocess.run(["openclaw", "agents", "delete", "--force", agent_id], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"cleanup_removed={len(set(remove))}")
PY
}

refresh_forecasts_if_needed() {
  local tmp_doctor="/tmp/planner-watchdog-doctor.json"
  curl -fsS "http://127.0.0.1:7779/api/doctor?refresh=1" >"$tmp_doctor" || return 0
  local needs_refresh
  needs_refresh="$(python3 - <<'PY' "$tmp_doctor"
import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
forecasts = (((payload.get("checks") or {}).get("product_value") or {}).get("metrics") or {}).get("forecasts") or {}
print("1" if forecasts.get("status") != "ok" else "0")
PY
)"
  if [ "$needs_refresh" != "1" ]; then
    return 0
  fi
  log "forecast_refresh_start"
  python3 apps/api/src/platform/legacy/jobs/stocks_prices_refresh.py --force --timeframe 1y >>"$LOG_FILE" 2>&1 || true
  curl -fsS "http://127.0.0.1:8050/api/forecasts?limit=5" >/dev/null || true
  log "forecast_refresh_done"
}

trigger_planner_if_needed() {
  local tmp_status="/tmp/planner-watchdog-status.json"
  local tmp_doctor="/tmp/planner-watchdog-doctor.json"
  curl -fsS "http://127.0.0.1:7779/api/status" >"$tmp_status" || return 0
  curl -fsS "http://127.0.0.1:7779/api/doctor?refresh=1" >"$tmp_doctor" || return 0
  python3 - <<'PY' "$tmp_status" "$tmp_doctor"
import json, pathlib, sys
status = json.loads(pathlib.Path(sys.argv[1]).read_text())
doctor = json.loads(pathlib.Path(sys.argv[2]).read_text())
pd = status.get("planner_dispatch") or {}
active = int(pd.get("active_subagents") or 0)
needs_dispatch = bool(pd.get("needs_dispatch"))
pd_status = str(pd.get("status") or "").lower()
doctor_pd = str((((doctor.get("checks") or {}).get("planner_dispatch") or {}).get("status") or "")).lower()
should_tick = active == 0 and (needs_dispatch or pd_status in {"degraded", "dispatch_needed"} or doctor_pd == "degraded")
print("1" if should_tick else "0")
print(pd_status)
print(active)
print(pd.get("recommended_next_action") or "none")
PY
}

log "watchdog_start interval=${INTERVAL_SECONDS}s duration=${DURATION_SECONDS}s"

while [ "$(date +%s)" -lt "$end_ts" ]; do
  cleanup_result="$(cleanup_orphan_capabilities 2>>"$LOG_FILE" || true)"
  [ -n "$cleanup_result" ] && log "$cleanup_result"
  refresh_forecasts_if_needed
  mapfile -t planner_probe < <(trigger_planner_if_needed)
  should_tick="${planner_probe[0]:-0}"
  pd_status="${planner_probe[1]:-unknown}"
  active_count="${planner_probe[2]:-0}"
  next_action="${planner_probe[3]:-none}"
  log "planner_probe status=$pd_status active=$active_count next=$next_action should_tick=$should_tick"
  if [ "$should_tick" = "1" ]; then
    log "planner_tick_start"
    bash scripts/fc_agent_tick.sh planner >>"$LOG_FILE" 2>&1 || true
    log "planner_tick_end"
  fi
  sleep "$INTERVAL_SECONDS"
done

log "watchdog_end"
