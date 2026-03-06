#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SESSION_PREFIX="${ADMIN_AGENTS_SESSION_PREFIX:-admin-agents-sync-}"
FALLBACK_SESSION="${ADMIN_AGENTS_FALLBACK_SESSION:-admin-agents-sync-cron}"
ROLE_NAME="admin-agents"
ROLE_RESPONSIBILITY="delivery-productivity"
STATE_DIR="${ADMIN_AGENTS_STATE_DIR:-/home/venom/.openclaw/cron/admin-state}"
CHAT_FILE="${ADMIN_AGENTS_CHAT_FILE:-docs/ops/ADMIN_TEAM_CHAT.md}"
ITER_FILE="${ADMIN_AGENTS_ITER_FILE:-docs/ops/ADMIN_TEAM_ITERATIONS.md}"
EVIDENCE_DIR="${ADMIN_AGENTS_EVIDENCE_DIR:-logs-codex-runs/admin-agents/ticks}"
ROLE_TRACE_DIR="${ADMIN_AGENTS_ROLE_TRACE_DIR:-logs-codex-runs/role-runner}"
ROLE_MEMORY_DIR="${ADMIN_AGENTS_ROLE_MEMORY_DIR:-$WORKDIR/memory/agents}"
ADMIN_MEMORY_FILE="${ROLE_MEMORY_DIR}/admin-agents.md"
ADMIN_MEMORY_LOCK_FILE="${STATE_DIR}/admin-agents.memory.lock"
PRIORITY_QUEUE_FILE="${ADMIN_AGENTS_PRIORITY_QUEUE_FILE:-docs/orchestrator-ops/priority-queue.json}"
EXEC_LATEST_FILE="${ADMIN_AGENTS_EXEC_LATEST_FILE:-docs/orchestrator-ops/executors-monitoring-latest.json}"
ROLE_TOPOLOGY_FILE="${ADMIN_AGENTS_ROLE_TOPOLOGY_FILE:-docs/orchestrator-ops/parallel-role-topology.json}"
ACTION_OWNER="${ADMIN_AGENTS_ACTION_OWNER:-adminapp-codex}"
ACTION_SCOPE_DEFAULT="${ADMIN_AGENTS_ACTION_SCOPE_DEFAULT:-runtime_stability}"
VERIFY_WAIT_SECONDS="${ADMIN_AGENTS_VERIFY_WAIT_SECONDS:-8}"
CAPTURE_LINES="${ADMIN_AGENTS_CAPTURE_LINES:-220}"
SESSION_INSPECT_LINES="${ADMIN_AGENTS_SESSION_INSPECT_LINES:-80}"
SESSION_IDLE_MARKER="${ADMIN_AGENTS_SESSION_IDLE_MARKER:-Improve documentation in @filename}"
SESSION_STALE_THRESHOLD_MINUTES="${ADMIN_AGENTS_SESSION_STALE_THRESHOLD_MINUTES:-60}"
RUNNING_STALE_SECONDS="${ADMIN_AGENTS_RUNNING_STALE_SECONDS:-330}"
NO_PROGRESS_THRESHOLD="${ADMIN_AGENTS_NO_PROGRESS_THRESHOLD:-3}"
NO_PROGRESS_FILE="${STATE_DIR}/admin-agents-no-progress-streak.txt"
LAST_ALERT_FILE="${STATE_DIR}/admin-agents-last-alert.txt"
LAST_DELIVERY_ALERT_FILE="${STATE_DIR}/admin-agents-last-delivery-alert.txt"
OPENCLAW_BIN="${ADMIN_AGENTS_OPENCLAW_BIN:-}"

cd "$WORKDIR"
mkdir -p "$STATE_DIR"
mkdir -p "$EVIDENCE_DIR"
mkdir -p "$ROLE_MEMORY_DIR"

if ! command -v tmux >/dev/null 2>&1; then
  echo "status=ERROR reason=tmux_missing"
  exit 5
fi

resolve_openclaw_bin() {
  local candidate=""
  if [[ -n "$OPENCLAW_BIN" && -x "$OPENCLAW_BIN" ]]; then
    printf '%s\n' "$OPENCLAW_BIN"
    return 0
  fi
  for candidate in \
    "/home/venom/.npm-global/bin/openclaw" \
    "${HOME}/.npm-global/bin/openclaw" \
    "$(command -v openclaw 2>/dev/null || true)" \
    "/usr/local/bin/openclaw" \
    "/usr/bin/openclaw" \
    "/bin/openclaw"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

if ! OPENCLAW_BIN="$(resolve_openclaw_bin)"; then
  echo "status=ERROR reason=openclaw_missing"
  exit 5
fi

list_sessions() {
  tmux list-sessions -F '#S' 2>/dev/null || tmux ls 2>/dev/null | cut -d: -f1
}

pick_session() {
  local sessions=""
  local picked=""
  sessions="$(list_sessions || true)"
  picked="$(printf '%s\n' "$sessions" | grep -E "^${SESSION_PREFIX}[0-9]{4}$" | tail -n 1 || true)"
  if [[ -z "$picked" ]]; then
    picked="$(printf '%s\n' "$sessions" | grep -E "^${SESSION_PREFIX}" | tail -n 1 || true)"
  fi
  if [[ -z "$picked" ]]; then
    picked="$FALLBACK_SESSION"
  fi
  printf '%s\n' "$picked"
}

latest_handoff_file() {
  ls -1t docs/ops/TMUX_HANDOFF_admin-agents_*.md 2>/dev/null | head -n 1 || true
}

	role_session_default() {
	  case "$1" in
	    planner) echo "codex_planner_cron" ;;
	    analyst) echo "codex_analyst_cron" ;;
	    architect) echo "codex_architect_cron" ;;
	    backend_engineer) echo "codex_backend_engineer_cron" ;;
	    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
	    data_analyst) echo "codex_data_analyst_cron" ;;
	    infra_engineer) echo "codex_infra_engineer_cron" ;;
	    integrator) echo "codex_integrator_cron" ;;
	    dev) echo "codex_dev_cron" ;;
	    tester) echo "codex_tester_cron" ;;
	    qa) echo "codex_qa_cron" ;;
	    clawsentinel) echo "clawsentinel" ;;
	    *) echo "" ;;
	  esac
	}

	role_trace_default() {
	  case "$1" in
	    *) echo "$1.live.log" ;;
	  esac
	}

ensure_session() {
  local session="$1"
  local handoff=""
  if tmux has-session -t "$session" 2>/dev/null; then
    return 0
  fi
  tmux new-session -d -s "$session" -c "$WORKDIR"
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  tmux send-keys -t "$session:0.0" "export ADMIN_ROLE=${ROLE_NAME}" C-m
  tmux send-keys -t "$session:0.0" "export ADMIN_RESPONSIBILITY=${ROLE_RESPONSIBILITY}" C-m
  tmux send-keys -t "$session:0.0" "printf '[ROLE] ${ROLE_NAME}\n[RESPONSIBILITY] delivery productivity owner\n[WORKSPACE] ${WORKDIR}\n\n'" C-m
  handoff="$(latest_handoff_file)"
  if [[ -n "$handoff" ]]; then
    tmux send-keys -t "$session:0.0" "cat '$handoff'" C-m
  fi
  tmux send-keys -t "$session:0.0" "echo '[READY] Session active'" C-m
}

pane_current_command() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]'
}

pane_pid() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_pid}" 2>/dev/null | tr -d '[:space:]'
}

agent_is_ready() {
  local target="$1"
  local cmd=""
  local pid=""
  local children=""
  cmd="$(pane_current_command "$target" || true)"
  if [[ "$cmd" == "codex" || "$cmd" == "node" ]]; then
    return 0
  fi
  pid="$(pane_pid "$target" || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    children="$(pgrep -P "$pid" -af 2>/dev/null || true)"
    if printf '%s\n' "$children" | grep -Eiq '(codex|node.*codex|openai.*codex)'; then
      return 0
    fi
  fi
  return 1
}

start_agent_if_needed() {
  local target="$1"
  if agent_is_ready "$target"; then
    return 0
  fi
  tmux send-keys -t "$target" C-c
  tmux send-keys -t "$target" "cd $WORKDIR" C-m
  tmux send-keys -t "$target" "codex --no-alt-screen" C-m
  sleep 3
}

inject_tick_prompt() {
  local target="$1"
  local tick="$2"
  local tmp=""
  local buf=""

  tmp="$(mktemp)"
  cat > "$tmp" <<EOF
ROLE=admin-agents.
Continue le travail admin-agents depuis l'historique tmux et les documents partages.
Focus uniquement sur logs RECENTS (pas anciens) pour les 12 cron rôles actifs.
Objectif du tick:
1) verifier l'etat des runs recents (errors/NO_DELTA/BLOCKED);
2) identifier le principal frein productivite;
3) identifier qui doit agir (adminapp-codex, admin-agents, clawsentinel) avant toute action;
4) remonter tout probleme d'execution (timeout, tmux reply unparseable, evidence manquante: EXEC_REPORT_MISSING/ISSUES_SUMMARY_MISSING/SUGGESTIONS_SUMMARY_MISSING, ou delivery evidence missing) + proposer une action concrete;
5) journaliser INTENT/DONE dans docs/ops/ADMIN_TEAM_CHAT.md et une ligne dans docs/ops/ADMIN_TEAM_ITERATIONS.md;
6) publier en fin de tick un rapport compact orienté incidents: exec_report=<resume>, issues=<none|liste_priorisee>, suggestions=<none|actions>.
Contraintes:
- garder les crons role sur gpt-5.3-spark et thinking high;
- garder le main agent OpenClaw sur gpt-5.2 + high;
- ne pas utiliser de commande git destructive.
TICK: ${tick}
EOF

  buf="admin_agents_tick_${tick}_$$"
  tmux load-buffer -b "$buf" "$tmp"
  tmux paste-buffer -d -b "$buf" -t "$target"
  tmux send-keys -t "$target" C-m
  rm -f "$tmp"
}

file_mtime() {
  local path="$1"
  if [[ -f "$path" ]]; then
    stat -c %Y "$path" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

pane_digest() {
  local target="$1"
  local lines="$2"
  tmux capture-pane -pt "$target" -S "-${lines}" 2>/dev/null | sha256sum | awk '{print $1}'
}

pane_contains_tick() {
  local target="$1"
  local tick="$2"
  tmux capture-pane -pt "$target" -S "-${CAPTURE_LINES}" 2>/dev/null | grep -Fq "TICK: ${tick}"
}

read_no_progress_streak() {
  if [[ -f "$NO_PROGRESS_FILE" ]]; then
    cat "$NO_PROGRESS_FILE" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

write_no_progress_streak() {
  local streak="$1"
  printf '%s\n' "$streak" > "$NO_PROGRESS_FILE"
}

maybe_append_chat_alert() {
  local severity="$1"
  local message="$2"
  local next="$3"
  local fingerprint="$4"
  local ts_local=""
  local last=""
  ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
  if [[ -f "$LAST_ALERT_FILE" ]]; then
    last="$(cat "$LAST_ALERT_FILE" 2>/dev/null || true)"
  fi
  if [[ "$fingerprint" == "$last" ]]; then
    return 0
  fi
  if [[ -f "$CHAT_FILE" ]]; then
    printf -- "- [%s] [admin-agents] TYPE: %s MSG: %s NEXT: %s.\n" "$ts_local" "$severity" "$message" "$next" >> "$CHAT_FILE"
  fi
  printf '%s\n' "$fingerprint" > "$LAST_ALERT_FILE"
}

deterministic_delivery_tick() {
  local tick="$1"
  local artifact=""
  local cron_json=""
  local now_epoch=0
  local role_total=0
  local role_enabled=0
  local role_ok=0
  local role_running=0
  local role_error=0
  local role_pending=0
  local exec_blockers=0
  local exec_blocker_roles="none"
  local exec_process_issues=0
  local exec_process_roles="none"
  local stale_running=0
  local stale_running_examples="none"
  local ready_total=0
  local queue_file_present=0
  local unhealthy="none"
  local session_total=0
  local session_present=0
  local session_missing=0
  local session_idle_generic=0
  local session_trace_recent=0
  local session_trace_stale=0
  local session_cmd_active=0
  local issue_examples="none"
  local top_issue="none"
  local next_action="keep_monitoring"
  local now_utc=""
  local fingerprint=""
  local last_delivery=""
  local ts_local=""
  local action_id=""
  local action_owner="$ACTION_OWNER"
  local action_scope="$ACTION_SCOPE_DEFAULT"
  local exec_report="none"
  local issues_report="none"
  local suggestions_report="none"
  local role_keys=()
  local role_sessions=()
  local role_traces=()
  local topology_roles=()
  local topo_role=""
  local topo_session=""
  local topo_trace=""
  local issue_samples=()
  local stale_samples=()
  local idx=0
  local role=""
  local session_name=""
  local trace_file=""
  local running_ms=""
  local running_age=0
  local running_role=""
  local pane_text=""
  local pane_cmd=""
  local trace_ts=""
  local trace_epoch=0
  local trace_age_min=0
  local has_backend_lane=0
  local has_frontend_lane=0

  artifact="${EVIDENCE_DIR}/admin-agents-${tick}.json"
  cron_json="$("$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  now_epoch="$(date -u +%s)"
  if [[ -f "$PRIORITY_QUEUE_FILE" ]]; then
    queue_file_present=1
    ready_total="$(jq '[.items[]? | select((.state // "") == "READY")] | length' "$PRIORITY_QUEUE_FILE" 2>/dev/null || echo 0)"
  fi
  if [[ ! "$ready_total" =~ ^[0-9]+$ ]]; then
    ready_total=0
  fi
  if [[ -f "$EXEC_LATEST_FILE" ]]; then
    exec_blockers="$(jq -r '.summary.blockers_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
    exec_blocker_roles="$(jq -r '(.summary.blocker_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo "none")"
    exec_process_issues="$(jq -r '.summary.process_issues_open // .summary.issues_open // 0' "$EXEC_LATEST_FILE" 2>/dev/null || echo 0)"
    exec_process_roles="$(jq -r '(.summary.process_issue_roles // .summary.issue_roles // []) | map(select(type=="string" and length>0)) | if length==0 then "none" else join(",") end' "$EXEC_LATEST_FILE" 2>/dev/null || echo "none")"
  fi
  if ! [[ "$exec_blockers" =~ ^[0-9]+$ ]]; then
    exec_blockers=0
  fi
  if ! [[ "$exec_process_issues" =~ ^[0-9]+$ ]]; then
    exec_process_issues=0
  fi

  mapfile -t topology_roles < <(jq -r '.roles[]? | select((.role // "") != "") | .role' "$ROLE_TOPOLOGY_FILE" 2>/dev/null || true)
  if [[ "${#topology_roles[@]}" -gt 0 ]]; then
    for topo_role in "${topology_roles[@]}"; do
      topo_session="$(jq -r --arg r "$topo_role" '.roles[]? | select(.role==$r) | .session_name // empty' "$ROLE_TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
      topo_trace="$(jq -r --arg r "$topo_role" '.roles[]? | select(.role==$r) | .trace_file // empty' "$ROLE_TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
      if [[ -z "$topo_session" ]]; then
        topo_session="$(role_session_default "$topo_role")"
      fi
      if [[ -z "$topo_trace" ]]; then
        topo_trace="$(role_trace_default "$topo_role")"
        topo_trace="${ROLE_TRACE_DIR}/${topo_trace}"
      fi
      role_keys+=("$topo_role")
      role_sessions+=("$topo_session")
      role_traces+=("$topo_trace")
    done
	  else
	    role_keys=("planner" "dev" "tester" "qa" "architect" "clawsentinel")
	    role_sessions=("codex_planner_cron" "codex_dev_cron" "codex_tester_cron" "codex_qa_cron" "codex_architect_cron" "clawsentinel")
	    role_traces=(
	      "${ROLE_TRACE_DIR}/planner.live.log"
	      "${ROLE_TRACE_DIR}/dev.live.log"
	      "${ROLE_TRACE_DIR}/tester.live.log"
	      "${ROLE_TRACE_DIR}/qa.live.log"
	      "${ROLE_TRACE_DIR}/architect.live.log"
	      "${ROLE_TRACE_DIR}/clawsentinel.live.log"
	    )
	  fi

  role_total="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.name // "") | test("-tmux-"))] | length' 2>/dev/null || echo 0)"
  role_enabled="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.name // "") | test("-tmux-")) | select(.enabled==true)] | length' 2>/dev/null || echo 0)"
  role_ok="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.name // "") | test("-tmux-")) | select(.state.lastStatus=="ok")] | length' 2>/dev/null || echo 0)"
  role_running="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.name // "") | test("-tmux-")) | select(.state.lastStatus=="running")] | length' 2>/dev/null || echo 0)"
  role_error="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.name // "") | test("-tmux-")) | select(.state.lastStatus=="error")] | length' 2>/dev/null || echo 0)"
  role_pending="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.name // "") | test("-tmux-")) | select(.state.lastStatus==null)] | length' 2>/dev/null || echo 0)"
  unhealthy="$(printf '%s' "$cron_json" | jq -r '[.jobs[]? | select((.name // "") | test("-tmux-")) | select((.state.lastStatus // "") == "error") | .name] | if length==0 then "none" else join(",") end' 2>/dev/null || echo "none")"

  while IFS=$'\t' read -r session_name running_role running_ms; do
    [[ -z "$running_ms" || "$running_ms" == "null" ]] && continue
    if ! [[ "$running_ms" =~ ^[0-9]+$ ]]; then
      continue
    fi
    running_age=$((now_epoch - (running_ms / 1000)))
    if [[ "$running_age" -lt "$RUNNING_STALE_SECONDS" ]]; then
      continue
    fi
    if [[ -z "$running_role" || "$running_role" == "null" ]]; then
      running_role="$(printf '%s' "$session_name" | sed -E 's/-tmux-loop$//' | tr '-' '_')"
    fi
    if pgrep -af "cron_tmux_role_runner.sh ${running_role}" >/dev/null 2>&1; then
      continue
    fi
    stale_running=$((stale_running + 1))
    if [[ "${#stale_samples[@]}" -lt 4 ]]; then
      stale_samples+=("${session_name}:${running_age}s")
    fi
  done < <(
    printf '%s' "$cron_json" \
      | jq -r '.jobs[]? | select((.name // "") | test("-tmux-loop$")) | [.name, (.agentId // "null"), (.state.runningAtMs // "null")] | @tsv' 2>/dev/null
  )

  if [[ "${#stale_samples[@]}" -gt 0 ]]; then
    stale_running_examples="$(printf '%s,' "${stale_samples[@]}")"
    stale_running_examples="${stale_running_examples%,}"
    if [[ "${#issue_samples[@]}" -lt 4 ]]; then
      issue_samples+=("stale_running:${stale_running_examples}")
    fi
  fi

  for role in "${role_keys[@]}"; do
    if [[ "$role" == "backend_engineer" || "$role" == "dev" ]]; then
      has_backend_lane=1
    fi
    if [[ "$role" == "frontend_engineer" ]]; then
      has_frontend_lane=1
    fi
  done

  for idx in "${!role_keys[@]}"; do
    role="${role_keys[$idx]}"
    session_name="${role_sessions[$idx]}"
    trace_file="${role_traces[$idx]}"
    session_total=$((session_total + 1))

    if [[ -n "$session_name" ]] && tmux has-session -t "$session_name" 2>/dev/null; then
      session_present=$((session_present + 1))
      pane_cmd="$(tmux display-message -p -t "${session_name}:0.0" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]')"
      if [[ "$pane_cmd" == "node" || "$pane_cmd" == "codex" ]]; then
        session_cmd_active=$((session_cmd_active + 1))
      fi
      pane_text="$(tmux capture-pane -pt "${session_name}:0.0" -S "-${SESSION_INSPECT_LINES}" 2>/dev/null || true)"
      if printf '%s\n' "$pane_text" | grep -Fq "$SESSION_IDLE_MARKER"; then
        session_idle_generic=$((session_idle_generic + 1))
        if [[ "${#issue_samples[@]}" -lt 4 ]]; then
          issue_samples+=("${role}:idle_prompt")
        fi
      fi
    else
      session_missing=$((session_missing + 1))
      if [[ "${#issue_samples[@]}" -lt 4 ]]; then
        if [[ -n "$session_name" ]]; then
          issue_samples+=("${role}:session_missing")
        else
          issue_samples+=("${role}:session_unknown")
        fi
      fi
    fi

    trace_epoch=0
    if [[ -f "$trace_file" ]]; then
      trace_ts="$(tail -n 1 "$trace_file" | awk '{print $1}' | tr -d '\r' || true)"
      if [[ "$trace_ts" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*Z$ ]]; then
        trace_epoch="$(date -ud "$trace_ts" +%s 2>/dev/null || echo 0)"
      fi
    fi
    if [[ "$trace_epoch" =~ ^[0-9]+$ ]] && [[ "$trace_epoch" -gt 0 ]]; then
      trace_age_min=$(( (now_epoch - trace_epoch) / 60 ))
      if [[ "$trace_age_min" -le "$SESSION_STALE_THRESHOLD_MINUTES" ]]; then
        session_trace_recent=$((session_trace_recent + 1))
      else
        session_trace_stale=$((session_trace_stale + 1))
        if [[ "${#issue_samples[@]}" -lt 4 ]]; then
          issue_samples+=("${role}:stale_${trace_age_min}m")
        fi
      fi
    else
      session_trace_stale=$((session_trace_stale + 1))
      if [[ "${#issue_samples[@]}" -lt 4 ]]; then
        issue_samples+=("${role}:trace_missing")
      fi
    fi
  done

  if [[ "${#issue_samples[@]}" -gt 0 ]]; then
    issue_examples="$(printf '%s,' "${issue_samples[@]}")"
    issue_examples="${issue_examples%,}"
  fi
  if [[ "$exec_blockers" -gt 0 ]]; then
    if [[ "${#issue_samples[@]}" -lt 4 ]]; then
      issue_samples+=("exec_blockers:${exec_blocker_roles}")
    fi
    issue_examples="$(printf '%s,' "${issue_samples[@]}")"
    issue_examples="${issue_examples%,}"
  fi

  if [[ "$role_total" -eq 0 && "$ready_total" -eq 0 ]]; then
    top_issue="none"
    next_action="keep_monitoring_no_ready_items"
  elif [[ "$exec_blockers" -gt 0 ]]; then
    top_issue="role_contract_blockers"
    next_action="force_run_blocked_roles_then_recheck"
  elif [[ "$stale_running" -gt 0 ]]; then
    top_issue="stale_running_jobs"
    if [[ "$has_backend_lane" -eq 1 && "$has_frontend_lane" -eq 1 ]]; then
      next_action="reset_stale_running_role_jobs_then_force_run_planner_backend_frontend"
    elif [[ "$has_backend_lane" -eq 1 ]]; then
      next_action="reset_stale_running_role_jobs_then_force_run_planner_backend"
    else
      next_action="reset_stale_running_role_jobs_then_force_run_planner_dev"
    fi
  elif [[ "$session_missing" -gt 0 ]]; then
    top_issue="sessions_missing"
    if [[ "$has_backend_lane" -eq 1 ]]; then
      next_action="recreate_missing_sessions_then_validate_one_role(backend_engineer)"
    else
      next_action="recreate_missing_sessions_then_validate_one_role(planner)"
    fi
  elif [[ "$session_present" -gt 0 && "$session_idle_generic" -ge "$session_present" ]]; then
    top_issue="sessions_idle_generic_prompt"
    next_action="reactivate_one_role_sequential(planner)_and_verify_new_role_output"
  elif [[ "$session_trace_stale" -ge 4 ]]; then
    top_issue="sessions_stale_no_recent_runner_activity"
    if [[ "$has_backend_lane" -eq 1 && "$has_frontend_lane" -eq 1 ]]; then
      next_action="force_run_planner_then_backend_and_frontend_then_confirm_live_logs_refresh"
    elif [[ "$has_backend_lane" -eq 1 ]]; then
      next_action="force_run_planner_then_backend_and_confirm_live_logs_refresh"
    else
      next_action="force_run_planner_then_dev_and_confirm_live_logs_refresh"
    fi
  elif [[ "$role_error" -gt 0 ]]; then
    top_issue="role_errors_present"
    next_action="force_run_failed_roles_then_recheck"
  elif [[ "$exec_process_issues" -gt 0 ]]; then
    top_issue="executor_process_issues"
    next_action="force_run_issue_roles_then_recheck"
  elif [[ "$role_pending" -gt 0 ]]; then
    top_issue="role_jobs_pending"
    next_action="verify_scheduler_lane_and_recent_runs"
  elif [[ "$role_total" -eq 0 && "$session_present" -gt 0 ]]; then
    top_issue="roles_disabled_admins_only_mode"
    next_action="if_delivery_needed_enable_sequential_mode_starting_planner"
  elif [[ "$role_total" -eq 0 ]]; then
    top_issue="role_jobs_missing"
    next_action="rebuild_role_cron_jobs_from_configure_script"
  elif [[ "$role_enabled" -eq 0 ]]; then
    top_issue="role_jobs_disabled"
    next_action="enable_roles_sequential_for_delivery_validation"
  fi
  case "$top_issue" in
    none)
      action_owner="none"
      action_scope="monitoring"
      ;;
    sessions_idle_generic_prompt)
      action_owner="clawsentinel"
      action_scope="quality_signal"
      ;;
    roles_disabled_admins_only_mode)
      action_owner="admin-agents"
      action_scope="delivery_governance"
      ;;
    role_contract_blockers|executor_process_issues|stale_running_jobs|sessions_missing|role_errors_present|role_jobs_pending|role_jobs_missing|role_jobs_disabled|sessions_stale_no_recent_runner_activity)
      action_owner="adminapp-codex"
      action_scope="runtime_stability"
      ;;
    *)
      action_owner="$ACTION_OWNER"
      action_scope="$ACTION_SCOPE_DEFAULT"
      ;;
  esac
  exec_report="role_ok_${role_ok}_on_${role_total}_sessions_${session_present}_on_${session_total}_ready_${ready_total}_errors_${role_error}_stale_${stale_running}_exec_blockers_${exec_blockers}_exec_process_${exec_process_issues}"
  if [[ "$top_issue" != "none" ]]; then
    issues_report="${top_issue}"
    suggestions_report="${next_action}"
  fi
  action_id="AA_${tick}_${top_issue}"

  now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat > "$artifact" <<EOF
{
  "tick": "$tick",
  "generatedAtUtc": "$now_utc",
  "role": "$ROLE_NAME",
  "session": "$SESSION",
  "target": "$TARGET",
    "roleJobs": {
      "total": $role_total,
      "enabled": $role_enabled,
      "ok": $role_ok,
      "running": $role_running,
      "staleRunning": $stale_running,
      "error": $role_error,
      "pending": $role_pending,
      "unhealthy": "$unhealthy"
  },
  "queueInsights": {
    "file": "$PRIORITY_QUEUE_FILE",
    "filePresent": $queue_file_present,
    "readyItems": $ready_total
  },
  "executorSignals": {
    "file": "$EXEC_LATEST_FILE",
    "blockersOpen": $exec_blockers,
    "blockerRoles": "$exec_blocker_roles",
    "processIssuesOpen": $exec_process_issues,
    "processIssueRoles": "$exec_process_roles"
  },
    "sessionInsights": {
      "total": $session_total,
      "present": $session_present,
      "missing": $session_missing,
      "idleGenericPrompt": $session_idle_generic,
      "traceRecent": $session_trace_recent,
      "traceStale": $session_trace_stale,
      "staleRunningExamples": "$stale_running_examples",
      "cmdActive": $session_cmd_active,
      "staleThresholdMinutes": $SESSION_STALE_THRESHOLD_MINUTES,
      "issueExamples": "$issue_examples"
  },
  "handoffAction": {
    "id": "$action_id",
    "owner": "$action_owner",
    "scope": "$action_scope",
    "status": "SUGGESTED"
  },
  "executionReport": {
    "summary": "$exec_report",
    "issues": "$issues_report",
    "suggestions": "$suggestions_report",
    "issueExamples": "$issue_examples"
  },
  "topIssue": "$top_issue",
  "nextAction": "$next_action"
}
EOF

  fingerprint="${top_issue}|${role_total}|${role_enabled}|${role_error}|${unhealthy}|${ready_total}|${session_present}|${session_missing}|${session_idle_generic}|${session_trace_stale}|${stale_running}|${stale_running_examples}|${issue_examples}"
  if [[ -f "$LAST_DELIVERY_ALERT_FILE" ]]; then
    last_delivery="$(cat "$LAST_DELIVERY_ALERT_FILE" 2>/dev/null || true)"
  fi
  if [[ "$top_issue" != "none" && "$fingerprint" != "$last_delivery" ]]; then
    ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
    if [[ -f "$CHAT_FILE" ]]; then
      printf -- "- [%s] [admin-agents] TYPE: INFO MSG: deterministic tick %s => top_issue=%s, sessions=%s/%s, idle_prompt=%s, trace_stale=%s, role_enabled=%s/%s, role_error=%s, artifact=%s. NEXT: %s.\n" \
        "$ts_local" "$tick" "$top_issue" "$session_present" "$session_total" "$session_idle_generic" "$session_trace_stale" "$role_enabled" "$role_total" "$role_error" "$artifact" "$next_action" >> "$CHAT_FILE"
    fi
  fi
  printf '%s\n' "$fingerprint" > "$LAST_DELIVERY_ALERT_FILE"

  DETERMINISTIC_OK=1
  DETERMINISTIC_ARTIFACT="$artifact"
  DETERMINISTIC_ISSUE="$top_issue"
  DETERMINISTIC_NEXT_ACTION="$next_action"
  DETERMINISTIC_ACTION_ID="$action_id"
  DETERMINISTIC_ACTION_OWNER="$action_owner"
  DETERMINISTIC_ACTION_SCOPE="$action_scope"
  DETERMINISTIC_EXEC_REPORT="$exec_report"
  DETERMINISTIC_ISSUES="$issues_report"
  DETERMINISTIC_SUGGESTIONS="$suggestions_report"
}

DETERMINISTIC_OK=0
DETERMINISTIC_ARTIFACT=""
DETERMINISTIC_ISSUE="none"
DETERMINISTIC_NEXT_ACTION="keep_monitoring"
DETERMINISTIC_ACTION_ID=""
DETERMINISTIC_ACTION_OWNER="none"
DETERMINISTIC_ACTION_SCOPE="monitoring"
DETERMINISTIC_EXEC_REPORT="none"
DETERMINISTIC_ISSUES="none"
DETERMINISTIC_SUGGESTIONS="none"

SESSION="$(pick_session)"
ensure_session "$SESSION"
TARGET="${SESSION}:0.0"
start_agent_if_needed "$TARGET"
TICK="$(date -u +%Y%m%dT%H%M%SZ)"

pre_digest="$(pane_digest "$TARGET" "$CAPTURE_LINES")"
pre_chat_mtime="$(file_mtime "$CHAT_FILE")"
pre_iter_mtime="$(file_mtime "$ITER_FILE")"

inject_tick_prompt "$TARGET" "$TICK"
sleep "$VERIFY_WAIT_SECONDS"

post_digest="$(pane_digest "$TARGET" "$CAPTURE_LINES")"
post_chat_mtime="$(file_mtime "$CHAT_FILE")"
post_iter_mtime="$(file_mtime "$ITER_FILE")"

# Globals for stdout + memory (avoid unbound vars under set -u)
role_total=0
role_enabled=0
role_error=0
stale_running=0
session_total=0
session_present=0

deterministic_delivery_tick "$TICK"

# Auto-dispatch READY queue item to avoid long stalls (optional).
if [[ "${ADMIN_DISPATCHER_ENABLED:-${ADMIN_AGENTS_AUTO_DISPATCH_ENABLED:-1}}" -eq 1 ]]; then
  dispatch_out="$(bash scripts/admin_agents_auto_dispatch_ready.sh 2>&1 || true)"
  if [[ -n "${dispatch_out}" ]]; then
    dispatch_compact="$(printf '%s' "$dispatch_out" | tr '\n' '|' | sed 's/|*$//')"
    echo "admin_dispatcher ${dispatch_compact}"
  fi
fi

pane_changed=0
docs_changed=0
tick_seen=0
proof_changed=0

if [[ "$pre_digest" != "$post_digest" ]]; then
  pane_changed=1
fi
if [[ "$post_chat_mtime" -gt "$pre_chat_mtime" || "$post_iter_mtime" -gt "$pre_iter_mtime" ]]; then
  docs_changed=1
fi
if pane_contains_tick "$TARGET" "$TICK"; then
  tick_seen=1
fi
if [[ "$docs_changed" -eq 1 ]]; then
  proof_changed=1
fi
if [[ "$DETERMINISTIC_OK" -eq 1 && -n "$DETERMINISTIC_ARTIFACT" && -s "$DETERMINISTIC_ARTIFACT" ]]; then
  proof_changed=1
fi

streak="$(read_no_progress_streak)"
if [[ ! "$streak" =~ ^[0-9]+$ ]]; then
  streak=0
fi

if [[ "$proof_changed" -eq 1 ]]; then
  streak=0
else
  streak=$((streak + 1))
fi
write_no_progress_streak "$streak"

append_admin_agents_memory() {
  local status="$1"; shift
  local reason="$1"; shift
  local ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
  local line="$*"
  if [[ -z "$line" ]]; then
    line="(no_details)"
  fi
  local verdict="GO_WITH_CAUTION"
  local delta="none"
  local blocker_id="NONE"
  local next_action="admin-agents-tick-${TICK}"
  local issues="none"
  local suggestions="none"
  local stream_id="none"
  local task_id="${TICK}"

  if [[ "$status" == "OK" ]]; then
    verdict="PASS"
  elif [[ "$status" == "ERROR" || "$status" == "BLOCKED" ]]; then
    verdict="BLOCKED"
    blocker_id="ADMIN_AGENTS_${status}"
  fi
  if [[ -n "${DETERMINISTIC_ISSUE:-}" && "${DETERMINISTIC_ISSUE}" != "none" ]]; then
    issues="${DETERMINISTIC_ISSUE}"
  fi
  if [[ -n "${DETERMINISTIC_ISSUES:-}" && "${DETERMINISTIC_ISSUES}" != "none" ]]; then
    issues="${DETERMINISTIC_ISSUES}"
  fi
  if [[ -n "${DETERMINISTIC_SUGGESTIONS:-}" && "${DETERMINISTIC_SUGGESTIONS}" != "none" ]]; then
    suggestions="${DETERMINISTIC_SUGGESTIONS}"
  fi
  if [[ -n "${DETERMINISTIC_ACTION_ID:-}" ]]; then
    task_id="${DETERMINISTIC_ACTION_ID}"
  fi
  if [[ -n "${DETERMINISTIC_ACTION_OWNER:-}" ]]; then
    stream_id="${DETERMINISTIC_ACTION_OWNER}"
  fi
  if [[ -n "${reason:-}" ]]; then
    delta="$(printf '%s' "$reason" | tr -s ' ')"
  fi

  if command -v python3 >/dev/null 2>&1 && [[ -f "scripts/role_memory_append.py" ]]; then
    local tmp=""
    tmp="$(mktemp)"
    {
      printf 'STATUS: %s\n' "$status"
      printf 'DELTA: %s\n' "$delta"
      printf 'VERDICT: %s\n' "$verdict"
      printf 'BLOCKER_ID: %s\n' "$blocker_id"
      printf 'NEXT_ACTION_UNIQUE: %s\n' "$next_action"
      printf 'EVIDENCE: stream_id=%s; task_id=%s; exec_report=%s; reason=%s; issues=%s; suggestions=%s\n' \
        "$stream_id" \
        "$task_id" \
        "$(printf '%s' "$line" | tr -d '\r' | tr '\n' ' ' | tr ';' ',' | tr -s ' ')" \
        "$reason" \
        "$issues" \
        "$suggestions"
    } > "$tmp"
    python3 scripts/role_memory_append.py \
      "admin-agents" \
      "admin-agents-tick" \
      "$tmp" \
      "$ADMIN_MEMORY_FILE" \
      "$ADMIN_MEMORY_LOCK_FILE" \
      "$ts_local" >/dev/null 2>&1 || true
    rm -f "$tmp"
    return 0
  fi

  if command -v flock >/dev/null 2>&1; then
    {
      exec 9>"$ADMIN_MEMORY_LOCK_FILE"
      flock -x 9
      if [[ ! -f "$ADMIN_MEMORY_FILE" ]]; then
        printf '# admin-agents\n\n' > "$ADMIN_MEMORY_FILE"
      fi
      printf -- "- [%s] status=%s reason=%s %s\n" "$ts_local" "$status" "$reason" "$line" >> "$ADMIN_MEMORY_FILE"
      python3 - "$ADMIN_MEMORY_FILE" <<'PY' 2>/dev/null || true
import sys
from pathlib import Path
p=Path(sys.argv[1])
lines=p.read_text(encoding='utf-8',errors='ignore').splitlines(True)
if len(lines) <= 900:
    raise SystemExit(0)
head=lines[:40]
tail=lines[-760:]
p.write_text(''.join(head+['\n']+tail),encoding='utf-8')
PY
    }
  else
    if [[ ! -f "$ADMIN_MEMORY_FILE" ]]; then
      printf '# admin-agents\n\n' > "$ADMIN_MEMORY_FILE"
    fi
    printf -- "- [%s] status=%s reason=%s %s\n" "$ts_local" "$status" "$reason" "$line" >> "$ADMIN_MEMORY_FILE"
  fi
}

mem_common="tick=${TICK} sessions=${session_present}/${session_total} role_enabled=${role_enabled}/${role_total} role_error=${role_error} stale_running=${stale_running} top_issue=${DETERMINISTIC_ISSUE} next_action=${DETERMINISTIC_NEXT_ACTION} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} artifact=${DETERMINISTIC_ARTIFACT}"

if [[ "$tick_seen" -ne 1 || "$pane_changed" -ne 1 ]]; then
  if [[ "$proof_changed" -eq 1 ]]; then
    append_admin_agents_memory "WARN" "tick_not_observed_but_proof_changed" "$mem_common"
    echo "status=WARN role=${ROLE_NAME} session=${SESSION} target=${TARGET} tick=${TICK} pane_changed=${pane_changed} tick_seen=${tick_seen} docs_changed=${docs_changed} proof_changed=${proof_changed} no_progress_streak=${streak} deterministic_issue=${DETERMINISTIC_ISSUE} action_id=${DETERMINISTIC_ACTION_ID} action_owner=${DETERMINISTIC_ACTION_OWNER} action_scope=${DETERMINISTIC_ACTION_SCOPE} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} next_action=${DETERMINISTIC_NEXT_ACTION} artifact=${DETERMINISTIC_ARTIFACT} reason=tick_not_observed_but_proof_changed"
    exit 0
  fi
  maybe_append_chat_alert \
    "BLOCKER" \
    "tick ${TICK} non observe en tmux (pane_changed=${pane_changed}, tick_seen=${tick_seen})" \
    "verifier soumission codex dans la session ${SESSION}" \
    "BLOCKED|tick=${TICK}|pane_changed=${pane_changed}|tick_seen=${tick_seen}"
  append_admin_agents_memory "ERROR" "tick_not_observed" "$mem_common"
  echo "status=ERROR role=${ROLE_NAME} session=${SESSION} target=${TARGET} tick=${TICK} pane_changed=${pane_changed} tick_seen=${tick_seen} docs_changed=${docs_changed} proof_changed=${proof_changed} no_progress_streak=${streak} deterministic_issue=${DETERMINISTIC_ISSUE} action_id=${DETERMINISTIC_ACTION_ID} action_owner=${DETERMINISTIC_ACTION_OWNER} action_scope=${DETERMINISTIC_ACTION_SCOPE} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} next_action=${DETERMINISTIC_NEXT_ACTION} artifact=${DETERMINISTIC_ARTIFACT} reason=tick_not_observed"
  exit 6
fi

if [[ "$proof_changed" -ne 1 && "$streak" -ge "$NO_PROGRESS_THRESHOLD" ]]; then
  maybe_append_chat_alert \
    "BLOCKER" \
    "aucune preuve de livraison admin-agents depuis ${streak} ticks (chat/iterations inchanges)" \
    "forcer une action admin concrete puis revalider" \
    "BLOCKED|streak=${streak}|session=${SESSION}"
  append_admin_agents_memory "BLOCKED" "no_delivery_evidence" "$mem_common"
  echo "status=BLOCKED role=${ROLE_NAME} session=${SESSION} target=${TARGET} tick=${TICK} pane_changed=${pane_changed} tick_seen=${tick_seen} docs_changed=${docs_changed} proof_changed=${proof_changed} no_progress_streak=${streak} deterministic_issue=${DETERMINISTIC_ISSUE} action_id=${DETERMINISTIC_ACTION_ID} action_owner=${DETERMINISTIC_ACTION_OWNER} action_scope=${DETERMINISTIC_ACTION_SCOPE} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} next_action=${DETERMINISTIC_NEXT_ACTION} artifact=${DETERMINISTIC_ARTIFACT} reason=no_delivery_evidence"
  exit 7
fi

if [[ "$proof_changed" -ne 1 ]]; then
  append_admin_agents_memory "WARN" "no_delivery_evidence_yet" "$mem_common"
  echo "status=WARN role=${ROLE_NAME} session=${SESSION} target=${TARGET} tick=${TICK} pane_changed=${pane_changed} tick_seen=${tick_seen} docs_changed=${docs_changed} proof_changed=${proof_changed} no_progress_streak=${streak} deterministic_issue=${DETERMINISTIC_ISSUE} action_id=${DETERMINISTIC_ACTION_ID} action_owner=${DETERMINISTIC_ACTION_OWNER} action_scope=${DETERMINISTIC_ACTION_SCOPE} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} next_action=${DETERMINISTIC_NEXT_ACTION} artifact=${DETERMINISTIC_ARTIFACT} reason=no_delivery_evidence_yet"
  exit 0
fi

if [[ "$DETERMINISTIC_ISSUE" != "none" ]]; then
  append_admin_agents_memory "WARN" "deterministic_issue_detected" "$mem_common"
  echo "status=WARN role=${ROLE_NAME} session=${SESSION} target=${TARGET} tick=${TICK} pane_changed=${pane_changed} tick_seen=${tick_seen} docs_changed=${docs_changed} proof_changed=${proof_changed} no_progress_streak=${streak} deterministic_issue=${DETERMINISTIC_ISSUE} action_id=${DETERMINISTIC_ACTION_ID} action_owner=${DETERMINISTIC_ACTION_OWNER} action_scope=${DETERMINISTIC_ACTION_SCOPE} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} next_action=${DETERMINISTIC_NEXT_ACTION} artifact=${DETERMINISTIC_ARTIFACT} reason=deterministic_issue_detected"
  exit 0
fi

append_admin_agents_memory "OK" "ok" "$mem_common"

echo "status=OK role=${ROLE_NAME} session=${SESSION} target=${TARGET} tick=${TICK} pane_changed=${pane_changed} tick_seen=${tick_seen} docs_changed=${docs_changed} proof_changed=${proof_changed} no_progress_streak=${streak} deterministic_issue=${DETERMINISTIC_ISSUE} action_id=${DETERMINISTIC_ACTION_ID} action_owner=${DETERMINISTIC_ACTION_OWNER} action_scope=${DETERMINISTIC_ACTION_SCOPE} exec_report=${DETERMINISTIC_EXEC_REPORT} issues=${DETERMINISTIC_ISSUES} suggestions=${DETERMINISTIC_SUGGESTIONS} next_action=${DETERMINISTIC_NEXT_ACTION} artifact=${DETERMINISTIC_ARTIFACT}"
