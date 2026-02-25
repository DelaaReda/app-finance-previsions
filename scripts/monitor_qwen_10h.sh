#!/usr/bin/env bash
set -euo pipefail
ROOT="/Users/venom/Documents/analyse-financiere"
LOG="$ROOT/logs-qwen-runs/monitor-$(date +%Y%m%d-%H%M%S).log"
STATE="$ROOT/logs-qwen-runs/monitor-state.json"
mkdir -p "$ROOT/logs-qwen-runs"
start_ts=$(date +%s)
end_ts=$((start_ts + 10*3600))
last_run_id=""
last_mtime=0
stale_count=0

echo "[START] $(date '+%Y-%m-%dT%H:%M:%S%z') monitoring 10h" | tee -a "$LOG"

while [ "$(date +%s)" -lt "$end_ts" ]; do
  now=$(date '+%Y-%m-%dT%H:%M:%S%z')
  echo "\n[$now] cycle" | tee -a "$LOG"

  status_out=$(cd "$ROOT" && python3 scripts/qwen_orchestrator.py --tmux-cmd status 2>&1 || true)
  echo "$status_out" | tee -a "$LOG"

  runs_out=$(cd "$ROOT" && python3 scripts/analyze_orchestrator_runs.py --runs-dir finance-app/orchestrator-runs --limit 8 2>&1 || true)
  echo "$runs_out" | tee -a "$LOG"

  health_out=$(curl -sS http://localhost:8050/api/health 2>&1 || true)
  echo "$health_out" | tee -a "$LOG"

  latest_link="$ROOT/finance-app/orchestrator-runs/latest"
  anomaly=""

  if echo "$health_out" | rg -q '"ok":true'; then :; else anomaly+="backend_down;"; fi

  if [ -L "$latest_link" ]; then
    run_dir=$(readlink "$latest_link")
    run_id=$(basename "$run_dir")
    events="$run_dir/events.jsonl"
    if [ -f "$events" ]; then
      mtime=$(stat -f %m "$events" 2>/dev/null || echo 0)
      if [ "$run_id" = "$last_run_id" ]; then
        if [ "$mtime" -le "$last_mtime" ]; then
          stale_count=$((stale_count+1))
        else
          stale_count=0
        fi
      else
        stale_count=0
      fi
      last_run_id="$run_id"
      last_mtime="$mtime"
      if [ "$stale_count" -ge 3 ]; then
        anomaly+="run_stale_gt_60m:$run_id;"
      fi
    fi
  fi

  if echo "$status_out" | rg -q 'DOWN'; then
    anomaly+="tmux_role_down;"
  fi

  printf '{"ts":"%s","run_id":"%s","last_mtime":%s,"stale_count":%s,"anomaly":"%s"}\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$last_run_id" "$last_mtime" "$stale_count" "$anomaly" > "$STATE"

  if [ -n "$anomaly" ]; then
    echo "[ALERT] $anomaly" | tee -a "$LOG"
  else
    echo "[OK] no anomaly" | tee -a "$LOG"
  fi

  sleep 1200

done

echo "[END] $(date '+%Y-%m-%dT%H:%M:%S%z') monitoring completed" | tee -a "$LOG"
