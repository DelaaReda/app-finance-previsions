#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
cd "$ROOT"

ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M %Z')"

# Queue
queue_ready="none"
queue_blocked="none"
if [[ -f docs/orchestrator-ops/priority-queue.json ]]; then
  queue_ready="$(jq -r '[.items[]? | select((.state//"")=="READY") | (.id//"")] | map(select(length>0)) | join(",")' docs/orchestrator-ops/priority-queue.json 2>/dev/null || true)"
  queue_blocked="$(jq -r '[.items[]? | select((.state//"")=="BLOCKED") | (.id//"")] | map(select(length>0)) | join(",")' docs/orchestrator-ops/priority-queue.json 2>/dev/null || true)"
fi
[[ -n "$queue_ready" ]] || queue_ready="none"
[[ -n "$queue_blocked" ]] || queue_blocked="none"

# Gates
latest_gate="none"
if ls finance-app/openclaw-gates/*.md >/dev/null 2>&1; then
  gate_file="$(ls -1t finance-app/openclaw-gates/*.md 2>/dev/null | head -n 1 || true)"
  if [[ -n "$gate_file" ]]; then
    gate_verdict="$(rg -n '^VERDICT:' "$gate_file" | head -n 1 | sed 's/^.*VERDICT:[[:space:]]*//' | tr -d '\r' | sed 's/[[:space:]]*$//' )"
    latest_gate="$(basename "$gate_file" | sed 's/\.md$//' ):${gate_verdict:-UNKNOWN}"
  fi
fi

# Cron summary (deterministic)
cron_summary="$(bash scripts/cron_run_manager.sh status --stale-threshold 330 2>/dev/null | tail -n 1 || true)"
[[ -n "$cron_summary" ]] || cron_summary="CRON_STATUS_SUMMARY unknown"

# App
raw_app_status="$(./finance-copilot.sh status 2>/dev/null || true)"
raw_app_status="$(printf '%s\n' "$raw_app_status" | sed -r 's/\x1B\[[0-9;]*[mK]//g')"
backend_line="$(printf '%s\n' "$raw_app_status" | rg -m1 'Backend' | tr -s ' ' | sed 's/^ *//')"
frontend_line="$(printf '%s\n' "$raw_app_status" | rg -m1 'Frontend' | tr -s ' ' | sed 's/^ *//')"
[[ -n "$backend_line" ]] || backend_line="Backend:?"
[[ -n "$frontend_line" ]] || frontend_line="Frontend:?"

# Core role blockers (role-state)
role_blockers=""
for r in planner dev tester qa; do
  f="$HOME/.openclaw/cron/role-state/${r}.last_contract"
  b="NONE"
  if [[ -f "$f" ]]; then
    b="$(sed -n 's/^BLOCKER_ID:[[:space:]]*//p' "$f" | tail -n 1 | tr -d '\r' | sed 's/[[:space:]]*$//' )"
  fi
  [[ -n "$b" ]] || b="UNKNOWN"
  role_blockers+=" ${r}=${b}"
done
role_blockers="${role_blockers# }"

# Workstreams (counts)
ws="unknown"
if [[ -f docs/orchestrator-ops/parallel-workstreams.json ]]; then
  ws="$(jq -r '[.tasks[]?.state] | group_by(.) | map("\(.[0]):\(length)") | join(" ")' docs/orchestrator-ops/parallel-workstreams.json 2>/dev/null || echo unknown)"
  [[ -n "$ws" ]] || ws="unknown"
fi

# Top issue heuristic
issue="none"
owner="none"
action="none"

if printf '%s' "$cron_summary" | rg -q 'stale=[1-9]'; then
  issue="STALE_RUNNING"
  owner="adminapp-codex"
  action="reset_stale_running_role_jobs_then_force_run_planner_backend_frontend"
elif printf '%s' "$cron_summary" | rg -q 'failed=[1-9]|error=[1-9]'; then
  issue="CRON_ERROR"
  owner="adminapp-codex"
  action="inspect_failed_jobs_then_probe_roles"
elif [[ "$queue_ready" != "none" ]]; then
  issue="QUEUE_READY_NOT_DISPATCHED"
  owner="admin-agents"
  action="DISPATCH_READY_ITEM"
fi

cat <<EOF
TRIAGE ts=${ts_local}
QUEUE ready=${queue_ready} blocked=${queue_blocked}
GATE latest=${latest_gate}
CRON ${cron_summary}
APP ${backend_line} | ${frontend_line}
ROLES ${role_blockers}
WORKSTREAMS ${ws}
TOP issue=${issue} owner=${owner} next=${action}
FILES priority-queue=docs/orchestrator-ops/priority-queue.json role-state=~/.openclaw/cron/role-state gates=finance-app/openclaw-gates parallel=docs/orchestrator-ops/parallel-workstreams.json
EOF