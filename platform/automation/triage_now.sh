#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
EXEC_LATEST_FILE="docs/orchestrator-ops/executors-monitoring-latest.json"
TOOL_REQUESTS_FILE="docs/ops/AGENT_TOOL_REQUESTS.md"

GATES_DIR_CANONICAL="${ROOT}/evidence/gates/openclaw-gates"
GATES_DIR="${GATES_DIR_CANONICAL}"
if [[ ! -d "$GATES_DIR" ]]; then
  echo "WARN: gates directory missing: $GATES_DIR" >&2
  GATES_DIR="/dev/null"
fi

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
if [[ -d "$GATES_DIR" ]] && ls "$GATES_DIR"/*.md >/dev/null 2>&1; then
  gate_file="$(ls -1t "$GATES_DIR"/*.md 2>/dev/null | head -n 1 || true)"
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

# Executor monitoring snapshot (auto-published by role runner)
exec_blockers=0
exec_issues=0
exec_requests=0
exec_blocker_roles="none"
exec_issue_roles="none"
exec_request_roles="none"
if [[ -f "$EXEC_LATEST_FILE" ]]; then
  exec_blockers="$(jq -r '.summary.blockers_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
  exec_issues="$(jq -r '.summary.process_issues_open // .summary.issues_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
  exec_requests="$(jq -r '.summary.tool_skill_requests_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
  exec_blocker_roles="$(jq -r '(.summary.blocker_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo none)"
  exec_issue_roles="$(jq -r '(.summary.process_issue_roles // .summary.issue_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo none)"
  exec_request_roles="$(jq -r '(.summary.tool_skill_request_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo none)"
fi
if [[ ! "$exec_blockers" =~ ^[0-9]+$ ]]; then exec_blockers=0; fi
if [[ ! "$exec_issues" =~ ^[0-9]+$ ]]; then exec_issues=0; fi
if [[ ! "$exec_requests" =~ ^[0-9]+$ ]]; then exec_requests=0; fi
[[ -n "$exec_blocker_roles" ]] || exec_blocker_roles="none"
[[ -n "$exec_issue_roles" ]] || exec_issue_roles="none"
[[ -n "$exec_request_roles" ]] || exec_request_roles="none"

latest_request="none"
if [[ -f "$TOOL_REQUESTS_FILE" ]]; then
  latest_request="$(tail -n 1 "$TOOL_REQUESTS_FILE" | tr -d '\r' | sed 's/[[:space:]]*$//' )"
fi
[[ -n "$latest_request" ]] || latest_request="none"

# Workstreams (counts)
ws="unknown"
if [[ -f docs/orchestrator-ops/parallel-workstreams.json ]]; then
  ws="$(jq -r '[.tasks[]?.state] | group_by(.) | map("\(.[0]):\(length)") | join(" ")' docs/orchestrator-ops/parallel-workstreams.json 2>/dev/null || echo unknown)"
  [[ -n "$ws" ]] || ws="unknown"
fi

# Dispatch-needed check: queue READY but board has unassigned READY tasks
queue_ready_primary="$(printf '%s' "$queue_ready" | cut -d',' -f1)"
dispatch_needed=0
dispatch_ready_tasks="none"
if [[ "$queue_ready_primary" != "none" && -f docs/orchestrator-ops/parallel-workstreams.json ]]; then
  dispatch_ready_tasks="$(jq -r --arg pref "${queue_ready_primary}-" '[.tasks[]? | select(.state=="READY") | select((.id//"")|startswith($pref)) | select((.assignee//"")=="") | .id] | if length==0 then "none" else join(",") end' docs/orchestrator-ops/parallel-workstreams.json 2>/dev/null || echo none)"
  if [[ "$dispatch_ready_tasks" != "none" ]]; then
    dispatch_needed=1
  fi
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
elif [[ "$exec_blockers" -gt 0 ]]; then
  issue="ROLE_CONTRACT_BLOCKERS"
  owner="admin-agents"
  action="prioriser_resolution_blockers_roles_et_recheck"
elif [[ "$exec_requests" -gt 0 ]]; then
  issue="TOOL_SKILL_REQUESTS_PENDING"
  owner="admin-agents"
  action="traiter_demandes_outils_skills_puis_recheck"
elif [[ "$dispatch_needed" -eq 1 ]]; then
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
EXEC blockers=${exec_blockers} issues=${exec_issues} requests=${exec_requests} roles_blocked=${exec_blocker_roles} roles_issue=${exec_issue_roles} roles_request=${exec_request_roles}
REQUEST latest=${latest_request}
WORKSTREAMS ${ws}
DISPATCH needed=${dispatch_needed} ready_unassigned=${dispatch_ready_tasks}
TOP issue=${issue} owner=${owner} next=${action}
FILES priority-queue=docs/orchestrator-ops/priority-queue.json role-state=~/.openclaw/cron/role-state gates=${GATES_DIR} parallel=docs/orchestrator-ops/parallel-workstreams.json exec-latest=${EXEC_LATEST_FILE} tool-requests=${TOOL_REQUESTS_FILE}
EOF
