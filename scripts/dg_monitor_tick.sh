#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
STATE_DIR="${DG_MONITOR_STATE_DIR:-$HOME/.openclaw/state/dg_monitor}"
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

# Orchestrator health (core roles)
orch_health="$(python3 scripts/qwen_orchestrator.py --tmux-cmd health --status-format compact 2>/dev/null | tr '\n' ' ' | sed 's/  */ /g' || true)"
if [[ -z "$orch_health" ]]; then
  orch_health="VERDICT: UNKNOWN"
fi

# App status (backend/frontend)
app_status="$(./finance-copilot.sh status 2>/dev/null | rg -o 'Backend\s*:.*|Frontend\s*:.*' -n || true)"
app_compact="$(printf '%s\n' "$app_status" | tr '\n' ' ' | sed 's/  */ /g')"
[[ -n "$app_compact" ]] || app_compact="app_status=unknown"

line="DG_TICK ts_local=\"$now_local\" ts_utc=$now_iso cron_total=$total_jobs ok=$ok_jobs running=$running_jobs error=$error_jobs unhealthy=$unhealthy orch=\"$orch_health\" app=\"$app_compact\""

printf '%s\n' "$line"

# Persist latest (overwrite) + append history
printf '%s\n' "$line" > "$STATE_DIR/latest.txt"
printf '%s\n' "$line" >> "$STATE_DIR/ticks.log"