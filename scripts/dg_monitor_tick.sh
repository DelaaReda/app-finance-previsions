#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
STATE_DIR="${DG_MONITOR_STATE_DIR:-$HOME/.openclaw/state/dg_monitor}"
EXEC_LATEST_FILE="${DG_EXEC_LATEST_FILE:-docs/orchestrator-ops/executors-monitoring-latest.json}"
mkdir -p "$STATE_DIR"

cd "$ROOT"

now_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date)"
now_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Cron summary
cron_json="$(openclaw cron list --json 2>/dev/null || echo '{}')"

total_jobs="$(printf '%s' "$cron_json" | jq -r '.jobs | length' 2>/dev/null || echo 0)"
ok_jobs="$(printf '%s' "$cron_json" | jq -r '[.jobs[]? | select(.state.lastStatus=="ok")] | length' 2>/dev/null || echo 0)"
running_jobs="$(printf '%s' "$cron_json" | jq -r '[.jobs[]? | select(.state.lastStatus=="running")] | length' 2>/dev/null || echo 0)"
error_jobs="$(printf '%s' "$cron_json" | jq -r '[.jobs[]? | select(.state.lastStatus=="error")] | length' 2>/dev/null || echo 0)"

unhealthy="$(printf '%s' "$cron_json" \
  | jq -r '[.jobs[]? | select((.state.lastStatus!=null) and (.state.lastStatus!="ok") and (.state.lastStatus!="running")) | "\(.name):\(.state.lastStatus)" ] | if length==0 then "none" else join(",") end' 2>/dev/null || echo 'unknown')"

# Cron manager summary (includes stale detection)
cron_mgr_summary="$(bash scripts/cron_run_manager.sh status --stale-threshold 330 2>/dev/null | tail -n 1 || true)"
[[ -n "$cron_mgr_summary" ]] || cron_mgr_summary="CRON_STATUS_SUMMARY unknown"

# App status (backend/frontend) — strip ANSI color codes
raw_app_status="$(./finance-copilot.sh status 2>/dev/null || true)"
raw_app_status="$(printf '%s\n' "$raw_app_status" | sed -r 's/\x1B\[[0-9;]*[mK]//g')"
backend_line="$(printf '%s\n' "$raw_app_status" | rg -m1 'Backend' | tr -s ' ' | sed 's/^ *//')"
frontend_line="$(printf '%s\n' "$raw_app_status" | rg -m1 'Frontend' | tr -s ' ' | sed 's/^ *//')"
if [[ -n "$backend_line" || -n "$frontend_line" ]]; then
  app_compact="${backend_line:-Backend:?} | ${frontend_line:-Frontend:?}"
else
  app_compact="app_status=unknown"
fi

exec_blockers=0
exec_issues=0
exec_requests=0
exec_blocker_roles="none"
exec_issue_roles="none"
exec_request_roles="none"
if [[ -f "$EXEC_LATEST_FILE" ]]; then
  exec_blockers="$(jq -r '.summary.blockers_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
  exec_issues="$(jq -r '.summary.issues_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
  exec_requests="$(jq -r '.summary.tool_skill_requests_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
  exec_blocker_roles="$(jq -r '(.summary.blocker_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo none)"
  exec_issue_roles="$(jq -r '(.summary.issue_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo none)"
  exec_request_roles="$(jq -r '(.summary.tool_skill_request_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo none)"
fi
if [[ ! "$exec_blockers" =~ ^[0-9]+$ ]]; then exec_blockers=0; fi
if [[ ! "$exec_issues" =~ ^[0-9]+$ ]]; then exec_issues=0; fi
if [[ ! "$exec_requests" =~ ^[0-9]+$ ]]; then exec_requests=0; fi
[[ -n "$exec_blocker_roles" ]] || exec_blocker_roles="none"
[[ -n "$exec_issue_roles" ]] || exec_issue_roles="none"
[[ -n "$exec_request_roles" ]] || exec_request_roles="none"

line="DG_TICK ts_local=\"$now_local\" ts_utc=$now_iso cron_total=$total_jobs ok=$ok_jobs running=$running_jobs error=$error_jobs unhealthy=$unhealthy exec_blockers=$exec_blockers exec_issues=$exec_issues exec_requests=$exec_requests exec_blocker_roles=$exec_blocker_roles exec_issue_roles=$exec_issue_roles exec_request_roles=$exec_request_roles cron_mgr=\"$cron_mgr_summary\" app=\"$app_compact\""

printf '%s\n' "$line"

# Persist latest (overwrite) + append history
printf '%s\n' "$line" > "$STATE_DIR/latest.txt"
printf '%s\n' "$line" >> "$STATE_DIR/ticks.log"
