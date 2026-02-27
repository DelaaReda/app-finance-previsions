#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
cd "$ROOT"

STATE_DIR="${DG_ROUTER_STATE_DIR:-$HOME/.openclaw/state/dg_router}"
mkdir -p "$STATE_DIR"

CHAT_FILE="${DG_ROUTER_CHAT_FILE:-$ROOT/docs/ops/ADMIN_TEAM_CHAT.md}"
EXEC_LATEST="${DG_ROUTER_EXEC_LATEST_FILE:-$ROOT/docs/orchestrator-ops/executors-monitoring-latest.json}"

# Admin tmux sessions (best effort)
S_ADMINAPP="${DG_ROUTER_TMUX_ADMINAPP:-adminapp_codex_sync}"
S_ADMINAGENTS="${DG_ROUTER_TMUX_ADMINAGENTS:-admin-agents-sync-cron}"
S_SENTINEL="${DG_ROUTER_TMUX_SENTINEL:-clawsentinel}"

now_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date)"
now_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

triage="$(bash scripts/triage_now.sh 2>/dev/null || true)"
if [[ -z "$triage" ]]; then
  echo "DG_ROUTER status=ERROR reason=triage_empty"
  exit 0
fi

top_line="$(printf '%s\n' "$triage" | sed -n 's/^TOP //p' | head -n 1)"
queue_ready="$(printf '%s\n' "$triage" | sed -n 's/^QUEUE ready=\([^ ]*\).*/\1/p' | head -n 1)"
app_line="$(printf '%s\n' "$triage" | sed -n 's/^APP //p' | head -n 1)"

dispatch_needed="$(printf '%s\n' "$triage" | sed -n 's/^DISPATCH needed=\([0-9][0-9]*\).*/\1/p' | head -n 1)"
dispatch_needed="${dispatch_needed:-0}"
ready_unassigned="$(printf '%s\n' "$triage" | sed -n 's/^DISPATCH needed=[0-9][0-9]* ready_unassigned=\(.*\)$/\1/p' | head -n 1)"
ready_unassigned="${ready_unassigned:-none}"

issue="$(printf '%s' "$top_line" | sed -n 's/.*issue=\([^ ]*\).*/\1/p')"
owner="$(printf '%s' "$top_line" | sed -n 's/.*owner=\([^ ]*\).*/\1/p')"
next_action="$(printf '%s' "$top_line" | sed -n 's/.*next=\([^ ]*\).*/\1/p')"

# Exec monitoring summary (roles blocked / roles with issues)
roles_blocked="none"
roles_issue="none"
if [[ -f "$EXEC_LATEST" ]]; then
  roles_blocked="$(jq -r '[.roles|to_entries[] | select((.value.blocker_id//"NONE")!="NONE") | .key] | join(",")' "$EXEC_LATEST" 2>/dev/null || true)"
  roles_issue="$(jq -r '[.roles|to_entries[] | select((.value.issues//"none")!="none" and (.value.issues//"")!="") | .key] | join(",")' "$EXEC_LATEST" 2>/dev/null || true)"
fi
[[ -n "$roles_blocked" ]] || roles_blocked="none"
[[ -n "$roles_issue" ]] || roles_issue="none"

# Cron thinking drift check (flag any enabled job still on thinking=low)
thinking_low="$(openclaw cron list --json 2>/dev/null | jq -r '[.jobs[]? | select(.enabled==true) | select((.payload.thinking//"")=="low") | .name] | join(",")' 2>/dev/null || true)"
[[ -n "$thinking_low" ]] || thinking_low="none"

# Fingerprint to avoid spamming identical directives
fingerprint="issue=${issue}|ready=${queue_ready}|dispatch_needed=${dispatch_needed}|unassigned=${ready_unassigned}|blocked=${roles_blocked}|low=${thinking_low}|next=${next_action}"
last_fp="$(cat "$STATE_DIR/last_fingerprint.txt" 2>/dev/null || true)"
if [[ -n "$last_fp" && "$last_fp" == "$fingerprint" ]]; then
  echo "DG_ROUTER status=NOOP ts=$now_local"
  exit 0
fi
echo "$fingerprint" > "$STATE_DIR/last_fingerprint.txt"

# Build directives (main -> admins) based on triage + exec signals
id="DG_DIR_$(date -u +%Y%m%dT%H%M%SZ)"

msg_common="id=${id} ts=${now_local} issue=${issue:-unknown} ready=${queue_ready:-none} dispatch_needed=${dispatch_needed} ready_unassigned=${ready_unassigned} roles_blocked=${roles_blocked} roles_issue=${roles_issue} app=\"${app_line}\""

msg_adminagents="MAIN ROUTE ${msg_common} | ACTION: (1) si ready!=none => claim tasks READY et DISPATCH (board: parallel_workstreams). (2) si roles_blocked!=none => clear blockers en rerun role-specifique avec preuves. next=${next_action:-none}"

msg_adminapp="MAIN ROUTE ${msg_common} | ACTION: (1) if stale/error/timeout -> run stale sweep apply + recheck cron_run_manager status. (2) if thinking_low!=none -> patch thinking to xhigh. next=${next_action:-none}"

msg_sentinel="MAIN ROUTE ${msg_common} | ACTION: surveiller répétition blockers >2 ticks, et dérives thinking/model; escalade TYPE: BLOCKER avec exec_issue code + evidence. next=${next_action:-none}"

# Optional: force-run admin-agents supervisor when dispatch is needed.
ADMIN_AGENTS_CRON_NAME="${DG_ROUTER_ADMIN_AGENTS_CRON_NAME:-admin-agents-supervisor-15m}"
FORCE_RUN_COOLDOWN_SECONDS="${DG_ROUTER_FORCE_RUN_COOLDOWN_SECONDS:-540}"
FORCE_RUN_ENABLED="${DG_ROUTER_FORCE_RUN_ADMIN_AGENTS_ON_DISPATCH:-1}"
FORCE_RUN_STATE_FILE="$STATE_DIR/last_force_run_admin_agents_epoch.txt"

maybe_force_run_admin_agents() {
  local now_epoch
  now_epoch="$(date -u +%s)"
  local last_epoch=0
  if [[ -f "$FORCE_RUN_STATE_FILE" ]]; then
    last_epoch="$(cat "$FORCE_RUN_STATE_FILE" 2>/dev/null || echo 0)"
  fi
  if ! [[ "$last_epoch" =~ ^[0-9]+$ ]]; then
    last_epoch=0
  fi
  if [[ $((now_epoch - last_epoch)) -lt "$FORCE_RUN_COOLDOWN_SECONDS" ]]; then
    echo "cooldown"
    return 0
  fi
  # find id by name
  local cron_id=""
  cron_id="$(openclaw cron list --json 2>/dev/null | jq -r --arg name "$ADMIN_AGENTS_CRON_NAME" '.jobs[]? | select(.name==$name) | (.id // empty)' | head -n 1 || true)"
  if [[ -z "$cron_id" ]]; then
    echo "missing_id"
    return 0
  fi
  # Run; ok if already-running
  openclaw cron run --timeout 90000 "$cron_id" >/dev/null 2>&1 || true
  printf '%s\n' "$now_epoch" > "$FORCE_RUN_STATE_FILE"
  echo "forced"
}

force_run_status="none"
if [[ "$FORCE_RUN_ENABLED" -eq 1 && "$dispatch_needed" == "1" ]]; then
  force_run_status="$(maybe_force_run_admin_agents)"
fi

# Send to tmux safely (buffer paste)
send_tmux() {
  local session="$1"
  local text="$2"
  if ! command -v tmux >/dev/null 2>&1; then
    return 0
  fi
  if ! tmux has-session -t "$session" 2>/dev/null; then
    return 0
  fi
  local tmp buf
  tmp="$(mktemp)"
  printf '%s\n' "$text" > "$tmp"
  buf="dg_router_${session}_$$"
  tmux load-buffer -b "$buf" "$tmp"
  tmux paste-buffer -d -b "$buf" -t "$session:0.0"
  tmux send-keys -t "$session:0.0" C-m
  rm -f "$tmp"
}

send_tmux "$S_ADMINAGENTS" "$msg_adminagents"
send_tmux "$S_ADMINAPP" "$msg_adminapp"
send_tmux "$S_SENTINEL" "$msg_sentinel"

# Journal in ADMIN_TEAM_CHAT.md (single line, deterministic)
if [[ -f "$CHAT_FILE" ]]; then
  printf -- "- [%s] [main] TYPE: ROUTE MSG: %s\n" "$now_local" "$msg_common" >> "$CHAT_FILE"
fi

# stdout for cron summary
printf '%s\n' "DG_ROUTER status=ROUTED id=$id issue=${issue:-unknown} owner=${owner:-unknown} next=${next_action:-none} ready=${queue_ready:-none} dispatch_needed=${dispatch_needed} force_run_admin_agents=${force_run_status} blocked=${roles_blocked} thinking_low=${thinking_low}"
