#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

SESSION="${ADMINAPP_TMUX_SESSION:-adminapp_codex_sync}"
WINDOW="${ADMINAPP_TMUX_WINDOW:-adminapp-codex-main}"
HANDOFF_FILE="${ADMINAPP_HANDOFF_FILE:-docs/ops/TMUX_SESSION_HANDOFF_ADMINAPP_CODEX.md}"
CHAT_FILE="${ADMINAPP_CHAT_FILE:-docs/ops/ADMIN_TEAM_CHAT.md}"
STATE_DIR="${ADMINAPP_STATE_DIR:-/home/venom/.openclaw/cron/admin-state}"
LAST_ALERT_FILE="${STATE_DIR}/last-alert.txt"
ADMIN_AGENTS_CRON_ID="${ADMIN_AGENTS_CRON_ID:-838deae5-fa39-4052-b31d-66013faccee0}"
ADMIN_AGENTS_SUMMARY_OVERRIDE="${ADMINAPP_ADMIN_AGENTS_SUMMARY_OVERRIDE:-}"
AUTO_EXEC_ENABLED="${ADMINAPP_AUTO_EXEC_ENABLED:-1}"
ACTION_COOLDOWN_SECONDS="${ADMINAPP_ACTION_COOLDOWN_SECONDS:-900}"
ACTION_STALL_KEY_FILE="${STATE_DIR}/admin-action-stall-key.txt"
ACTION_STALL_COUNT_FILE="${STATE_DIR}/admin-action-stall-count.txt"
ACTION_LAST_EXEC_SIG_FILE="${STATE_DIR}/admin-action-last-exec-signature.txt"
ACTION_LAST_EXEC_TS_FILE="${STATE_DIR}/admin-action-last-exec-ts.txt"
ACTION_LAST_ROUTED_ID_FILE="${STATE_DIR}/admin-action-last-routed-id.txt"
ROLE_TRACE_DIR="${ADMINAPP_ROLE_TRACE_DIR:-logs-codex-runs/role-runner}"
PRIORITY_QUEUE_FILE="${ADMINAPP_PRIORITY_QUEUE_FILE:-docs/orchestrator-ops/priority-queue.json}"
OPENCLAW_BIN="${ADMINAPP_OPENCLAW_BIN:-}"
RUNNING_STALE_SECONDS="${ADMINAPP_RUNNING_STALE_SECONDS:-330}"
STALE_SWEEP_SCRIPT="${ADMINAPP_STALE_SWEEP_SCRIPT:-scripts/stale_cron_sweep.sh}"

mkdir -p "$STATE_DIR"

read_file_or_empty() {
  local path="$1"
  if [[ -f "$path" ]]; then
    cat "$path" 2>/dev/null || true
  fi
}

file_mtime() {
  local path="$1"
  if [[ -f "$path" ]]; then
    stat -c %Y "$path" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

update_action_stall_counter() {
  local key="$1"
  local prev_key=""
  local prev_count=0
  local new_count=1
  prev_key="$(read_file_or_empty "$ACTION_STALL_KEY_FILE")"
  if [[ -f "$ACTION_STALL_COUNT_FILE" ]]; then
    prev_count="$(cat "$ACTION_STALL_COUNT_FILE" 2>/dev/null || echo 0)"
  fi
  if [[ ! "$prev_count" =~ ^[0-9]+$ ]]; then
    prev_count=0
  fi
  if [[ -n "$key" && "$key" == "$prev_key" ]]; then
    new_count=$((prev_count + 1))
  fi
  printf '%s\n' "$key" > "$ACTION_STALL_KEY_FILE"
  printf '%s\n' "$new_count" > "$ACTION_STALL_COUNT_FILE"
  printf '%s\n' "$new_count"
}

reset_action_stall_counter() {
  : > "$ACTION_STALL_KEY_FILE"
  printf '0\n' > "$ACTION_STALL_COUNT_FILE"
}

action_cooldown_active() {
  local signature="$1"
  local now_epoch=0
  local last_sig=""
  local last_ts=0
  now_epoch="$(date -u +%s)"
  last_sig="$(read_file_or_empty "$ACTION_LAST_EXEC_SIG_FILE")"
  if [[ -f "$ACTION_LAST_EXEC_TS_FILE" ]]; then
    last_ts="$(cat "$ACTION_LAST_EXEC_TS_FILE" 2>/dev/null || echo 0)"
  fi
  if [[ ! "$last_ts" =~ ^[0-9]+$ ]]; then
    last_ts=0
  fi
  if [[ "$signature" == "$last_sig" && "$last_ts" -gt 0 ]]; then
    if [[ $((now_epoch - last_ts)) -lt "$ACTION_COOLDOWN_SECONDS" ]]; then
      return 0
    fi
  fi
  return 1
}

mark_action_executed_now() {
  local signature="$1"
  local now_epoch=0
  now_epoch="$(date -u +%s)"
  printf '%s\n' "$signature" > "$ACTION_LAST_EXEC_SIG_FILE"
  printf '%s\n' "$now_epoch" > "$ACTION_LAST_EXEC_TS_FILE"
}

route_handoff_to_chat() {
  local owner="$1"
  local issue="$2"
  local action="$3"
  local action_id="$4"
  local action_scope="$5"
  local ts_local=""
  local last_routed=""
  if [[ -z "$action_id" || "$action_id" == "none" ]]; then
    return 0
  fi
  last_routed="$(read_file_or_empty "$ACTION_LAST_ROUTED_ID_FILE")"
  if [[ "$last_routed" == "$action_id" ]]; then
    return 0
  fi
  if [[ ! -f "$CHAT_FILE" ]]; then
    return 0
  fi
  ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
  printf -- "- [%s] [adminapp-codex] TYPE: HANDOFF MSG: action %s routee vers %s (scope=%s, issue=%s). NEXT: %s.\n" \
    "$ts_local" "$action_id" "${owner:-unknown}" "${action_scope:-none}" "${issue:-none}" "${action:-none}" >> "$CHAT_FILE"
  printf '%s\n' "$action_id" > "$ACTION_LAST_ROUTED_ID_FILE"
}

run_role_probe_once() {
  local role="$1"
  local trace="$2"
  local pre_mtime=0
  local post_mtime=0
  local out=""
  pre_mtime="$(file_mtime "$trace")"
  out="$(TMUX_ROLE_AGENT_BIN=codex TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk PROMPT_TIMEOUT_SECONDS=25 RETRY_PROMPT_TIMEOUT_SECONDS=10 TMUX_ROLE_STALL_ABORT_SECONDS=10 SKIP_RETRY_ON_TIMEOUT=1 TMUX_ROLE_CODEX_EXEC_FALLBACK=0 TMUX_ROLE_CODEX_EXEC_RESUME=1 TMUX_ROLE_ALLOW_FILE_EDITS=0 bash scripts/cron_tmux_role_runner.sh "$role" 2>&1 || true)"
  post_mtime="$(file_mtime "$trace")"
  if [[ "$post_mtime" -gt "$pre_mtime" ]]; then
    return 0
  fi
  if printf '%s\n' "$out" | rg -q "ROLE=${role} .*VERDICT="; then
    return 0
  fi
  return 1
}

parse_sweep_field() {
  local summary="$1"
  local key="$2"
  printf '%s\n' "$summary" | sed -n "s/.*${key}=\\([0-9][0-9]*\\).*/\\1/p" | head -n 1
}

STALE_SWEEP_LAST_SUMMARY=""

run_stale_sweep_preview() {
  local out=""
  local summary=""
  local rc=0
  STALE_SWEEP_LAST_SUMMARY=""
  if [[ ! -x "$STALE_SWEEP_SCRIPT" ]]; then
    return 1
  fi
  set +e
  out="$(
    STALE_SWEEP_OPENCLAW_BIN="$OPENCLAW_BIN" \
    bash "$STALE_SWEEP_SCRIPT" --dry-run --threshold "$RUNNING_STALE_SECONDS" 2>/dev/null
  )"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    return 1
  fi
  summary="$(printf '%s\n' "$out" | rg '^SWEEP_SUMMARY ' | tail -n 1 || true)"
  if [[ -z "$summary" ]]; then
    return 1
  fi
  STALE_SWEEP_LAST_SUMMARY="$summary"
  return 0
}

run_stale_sweep_action() {
  local out=""
  local summary=""
  local rc=0
  local stale=0
  local reset_ok=0
  local reset_failed=0
  local skipped_live=0

  if [[ ! -x "$STALE_SWEEP_SCRIPT" ]]; then
    ACTION_EXEC_RESULT="failed"
    ACTION_EXEC_DETAILS="stale_sweep_script_missing"
    return 1
  fi

  set +e
  out="$(
    STALE_SWEEP_OPENCLAW_BIN="$OPENCLAW_BIN" \
    bash "$STALE_SWEEP_SCRIPT" --apply --threshold "$RUNNING_STALE_SECONDS" 2>&1
  )"
  rc=$?
  set -e

  summary="$(printf '%s\n' "$out" | rg '^SWEEP_SUMMARY ' | tail -n 1 || true)"
  if [[ -z "$summary" ]]; then
    ACTION_EXEC_RESULT="failed"
    ACTION_EXEC_DETAILS="stale_sweep_no_summary"
    return 1
  fi
  STALE_SWEEP_LAST_SUMMARY="$summary"

  stale="$(parse_sweep_field "$summary" "stale")"
  reset_ok="$(parse_sweep_field "$summary" "reset_ok")"
  reset_failed="$(parse_sweep_field "$summary" "reset_failed")"
  skipped_live="$(parse_sweep_field "$summary" "skipped_live")"

  if [[ ! "$stale" =~ ^[0-9]+$ ]]; then stale=0; fi
  if [[ ! "$reset_ok" =~ ^[0-9]+$ ]]; then reset_ok=0; fi
  if [[ ! "$reset_failed" =~ ^[0-9]+$ ]]; then reset_failed=0; fi
  if [[ ! "$skipped_live" =~ ^[0-9]+$ ]]; then skipped_live=0; fi

  ACTION_EXEC_DETAILS="stale_jobs=${stale};reset_ok=${reset_ok};reset_failed=${reset_failed};skip_live=${skipped_live}"
  if [[ $rc -eq 0 && "$reset_failed" -eq 0 ]]; then
    ACTION_EXEC_RESULT="done"
    return 0
  fi
  ACTION_EXEC_RESULT="failed"
  return 1
}

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

execute_admin_action() {
  local action="$1"
  ACTION_EXEC_RESULT="none"
  ACTION_EXEC_DETAILS="none"
  case "$action" in
    reset_stale_running_role_jobs_then_force_run_planner_backend_frontend)
      if run_stale_sweep_action && run_role_probe_once "planner" "${ROLE_TRACE_DIR}/planner.live.log" && run_role_probe_once "backend_engineer" "${ROLE_TRACE_DIR}/backend_engineer.live.log" && run_role_probe_once "frontend_engineer" "${ROLE_TRACE_DIR}/frontend_engineer.live.log"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner+backend+frontend_refresh_ok"
      else
        if [[ "$ACTION_EXEC_RESULT" == "none" || "$ACTION_EXEC_RESULT" == "done" ]]; then
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner_or_backend_or_frontend_refresh_failed"
        fi
      fi
      ;;
    reset_stale_running_role_jobs_then_force_run_planner_backend)
      if run_stale_sweep_action && run_role_probe_once "planner" "${ROLE_TRACE_DIR}/planner.live.log" && run_role_probe_once "backend_engineer" "${ROLE_TRACE_DIR}/backend_engineer.live.log"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner+backend_refresh_ok"
      else
        if [[ "$ACTION_EXEC_RESULT" == "none" || "$ACTION_EXEC_RESULT" == "done" ]]; then
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner_or_backend_refresh_failed"
        fi
      fi
      ;;
    reset_stale_running_role_jobs_then_force_run_planner_dev)
      if run_stale_sweep_action && run_role_probe_once "planner" "${ROLE_TRACE_DIR}/planner.live.log" && run_role_probe_once "dev" "${ROLE_TRACE_DIR}/dev.live.log"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner+dev_refresh_ok"
      else
        if [[ "$ACTION_EXEC_RESULT" == "none" || "$ACTION_EXEC_RESULT" == "done" ]]; then
          ACTION_EXEC_RESULT="failed"
          ACTION_EXEC_DETAILS="${ACTION_EXEC_DETAILS};planner_or_dev_refresh_failed"
        fi
      fi
      ;;
    force_run_planner_then_dev_and_confirm_live_logs_refresh)
      if run_role_probe_once "planner" "${ROLE_TRACE_DIR}/planner.live.log" && run_role_probe_once "dev" "${ROLE_TRACE_DIR}/dev.live.log"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="planner+dev_refresh_ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="planner_or_dev_refresh_failed"
      fi
      ;;
    force_run_planner_then_backend_and_confirm_live_logs_refresh)
      if run_role_probe_once "planner" "${ROLE_TRACE_DIR}/planner.live.log" && run_role_probe_once "backend_engineer" "${ROLE_TRACE_DIR}/backend_engineer.live.log"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="planner+backend_refresh_ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="planner_or_backend_refresh_failed"
      fi
      ;;
    force_run_planner_then_backend_and_frontend_then_confirm_live_logs_refresh)
      if run_role_probe_once "planner" "${ROLE_TRACE_DIR}/planner.live.log" && run_role_probe_once "backend_engineer" "${ROLE_TRACE_DIR}/backend_engineer.live.log" && run_role_probe_once "frontend_engineer" "${ROLE_TRACE_DIR}/frontend_engineer.live.log"; then
        ACTION_EXEC_RESULT="done"
        ACTION_EXEC_DETAILS="planner+backend+frontend_refresh_ok"
      else
        ACTION_EXEC_RESULT="failed"
        ACTION_EXEC_DETAILS="planner_or_backend_or_frontend_refresh_failed"
      fi
      ;;
    *)
      ACTION_EXEC_RESULT="unsupported"
      ACTION_EXEC_DETAILS="unsupported_action"
      ;;
  esac
}

if ! command -v tmux >/dev/null 2>&1; then
  echo "STATUS: BLOCKED"
  echo "DELTA: tmux_absent"
  echo "EVIDENCE: command=tmux missing_from_PATH"
  echo "RISKS: impossible de maintenir la session admin en continu"
  echo "NEXT: installer tmux ou corriger PATH"
  echo "VERDICT: BLOCKED"
  echo "BLOCKER_ID: TMUX_MISSING"
  echo "NEXT_ACTION_UNIQUE: ADMINAPP_FIX_TMUX_$(date +%Y%m%d%H%M%S)"
  exit 0
fi

if ! OPENCLAW_BIN="$(resolve_openclaw_bin)"; then
  echo "STATUS: BLOCKED"
  echo "DELTA: openclaw_absent"
  echo "EVIDENCE: command=openclaw missing_from_PATH"
  echo "RISKS: monitoring cron indisponible"
  echo "NEXT: installer openclaw CLI ou corriger PATH"
  echo "VERDICT: BLOCKED"
  echo "BLOCKER_ID: OPENCLAW_MISSING"
  echo "NEXT_ACTION_UNIQUE: ADMINAPP_FIX_OPENCLAW_$(date +%Y%m%d%H%M%S)"
  exit 0
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -c "$ROOT"
fi

if ! tmux list-windows -t "$SESSION" -F '#W' | rg -qx "$WINDOW"; then
  tmux rename-window -t "${SESSION}:0" "$WINDOW" >/dev/null 2>&1 || true
fi

tmux set-environment -t "$SESSION" ADMIN_ROLE adminapp-codex
tmux set-option -t "$SESSION" history-limit 200000 >/dev/null 2>&1 || true

if [[ -f "$HANDOFF_FILE" ]]; then
  tmux set-environment -t "$SESSION" ADMIN_HANDOFF_FILE "$HANDOFF_FILE"
fi

cron_json="$("$OPENCLAW_BIN" cron list --json)"
total_jobs="$(printf '%s' "$cron_json" | jq '.jobs | length')"
ok_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="ok")] | length')"
running_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.runningAtMs!=null)] | length')"
error_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="error")] | length')"
timeout_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.state.lastError // "") | test("timed out"; "i"))] | length')"
pending_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus==null)] | length')"
stale_running_jobs=0
stale_running_skipped_live=0
if run_stale_sweep_preview; then
  stale_running_jobs="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "stale")"
  stale_running_skipped_live="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "skipped_live")"
fi
if [[ ! "$stale_running_jobs" =~ ^[0-9]+$ ]]; then
  stale_running_jobs=0
fi
if [[ ! "$stale_running_skipped_live" =~ ^[0-9]+$ ]]; then
  stale_running_skipped_live=0
fi

stale_auto_exec_result="none"
stale_auto_exec_details="none"
if [[ "$AUTO_EXEC_ENABLED" == "1" && "$stale_running_jobs" -gt 0 ]]; then
  if run_stale_sweep_action; then
    stale_auto_exec_result="done"
  else
    stale_auto_exec_result="failed"
  fi
  stale_auto_exec_details="$ACTION_EXEC_DETAILS"

  cron_json="$("$OPENCLAW_BIN" cron list --json)"
  total_jobs="$(printf '%s' "$cron_json" | jq '.jobs | length')"
  ok_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="ok")] | length')"
  running_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.runningAtMs!=null)] | length')"
  error_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus=="error")] | length')"
  timeout_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select((.state.lastError // "") | test("timed out"; "i"))] | length')"
  pending_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[] | select(.state.lastStatus==null)] | length')"

  stale_running_jobs=0
  stale_running_skipped_live=0
  if run_stale_sweep_preview; then
    stale_running_jobs="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "stale")"
    stale_running_skipped_live="$(parse_sweep_field "$STALE_SWEEP_LAST_SUMMARY" "skipped_live")"
  fi
  if [[ ! "$stale_running_jobs" =~ ^[0-9]+$ ]]; then
    stale_running_jobs=0
  fi
  if [[ ! "$stale_running_skipped_live" =~ ^[0-9]+$ ]]; then
    stale_running_skipped_live=0
  fi
fi

queue_ready_items=0
if [[ -f "$PRIORITY_QUEUE_FILE" ]]; then
  queue_ready_items="$(jq '[.items[]? | select((.state // "") == "READY")] | length' "$PRIORITY_QUEUE_FILE" 2>/dev/null || echo 0)"
fi
if [[ ! "$queue_ready_items" =~ ^[0-9]+$ ]]; then
  queue_ready_items=0
fi

if [[ -n "$ADMIN_AGENTS_SUMMARY_OVERRIDE" ]]; then
  admin_agents_last_summary="$ADMIN_AGENTS_SUMMARY_OVERRIDE"
else
  admin_agents_last_summary="$("$OPENCLAW_BIN" cron runs --id "$ADMIN_AGENTS_CRON_ID" --limit 1 2>/dev/null | jq -r '.entries[0].summary // ""' 2>/dev/null || true)"
fi
admin_agents_blocked=0
admin_agents_signal_status="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*status=\([A-Z]*\).*/\1/p' | head -n 1)"
admin_agents_next_action="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*next_action=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_issue="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*deterministic_issue=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_action_id="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*action_id=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_action_owner="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*action_owner=\([^ ]*\).*/\1/p' | head -n 1)"
admin_agents_action_scope="$(printf '%s\n' "$admin_agents_last_summary" | sed -n 's/.*action_scope=\([^ ]*\).*/\1/p' | head -n 1)"
if printf '%s\n' "$admin_agents_last_summary" | rg -q 'status=(BLOCKED|ERROR|WARN)'; then
  admin_agents_blocked=1
fi
if [[ -z "$admin_agents_action_owner" ]]; then
  admin_agents_action_owner="none"
fi
if [[ -z "$admin_agents_action_scope" ]]; then
  admin_agents_action_scope="none"
fi
admin_issue_benign_when_no_ready=0
if [[ "$queue_ready_items" -eq 0 ]]; then
  case "$admin_agents_issue" in
    none|sessions_stale_no_recent_runner_activity|roles_disabled_admins_only_mode|role_jobs_missing|role_jobs_disabled|sessions_missing|sessions_idle_generic_prompt)
      admin_issue_benign_when_no_ready=1
      ;;
  esac
fi
if [[ "$admin_agents_blocked" -eq 1 && "$admin_issue_benign_when_no_ready" -eq 1 ]]; then
  admin_agents_blocked=0
fi
admin_action_owner_external=0
case "$admin_agents_action_owner" in
  admin-agents|clawsentinel)
    admin_action_owner_external=1
    ;;
esac

unhealthy_compact="$(printf '%s' "$cron_json" \
  | jq -r '[.jobs[] | select((.state.lastStatus!=null) and (.state.lastStatus!="ok") and (.state.lastStatus!="running")) | "\(.name):\(.state.lastStatus)"] | if length==0 then "none" else join(",") end')"
if [[ "$admin_agents_blocked" -eq 1 ]]; then
  admin_agents_signal="attention_signal"
  if [[ "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ]]; then
    admin_agents_signal="blocked_signal"
  fi
  if [[ "$unhealthy_compact" == "none" ]]; then
    unhealthy_compact="admin-agents-supervisor-15m:${admin_agents_signal}"
  else
    unhealthy_compact="${unhealthy_compact},admin-agents-supervisor-15m:${admin_agents_signal}"
  fi
fi

verdict="PASS"
status="DONE"
delta="monitor_tick_ok"
blocker_id="NONE"
risks="none"
next="continuer monitoring haute fréquence et traiter uniquement les jobs en erreur"
admin_action_result="$stale_auto_exec_result"
admin_action_details="$stale_auto_exec_details"
admin_action_repeat=0
if [[ "$queue_ready_items" -eq 0 ]]; then
  delta="monitor_no_ready_queue"
  next="aucun batch READY; garder admins actifs et attendre prochain dispatch"
fi
if [[ "$error_jobs" -gt 0 ]]; then
  verdict="GO_WITH_CAUTION"
  status="IN_PROGRESS"
  delta="errors_detected"
  blocker_id="CRON_ERRORS_PRESENT"
  risks="certains jobs cron en erreur récente"
  next="prioriser force-run ciblé sur les jobs en erreur puis vérifier la récupération"
fi
if [[ "$stale_running_jobs" -gt 0 ]]; then
  verdict="GO_WITH_CAUTION"
  status="IN_PROGRESS"
  delta="stale_running_detected"
  blocker_id="CRON_STALE_RUNNING_STATE"
  risks="jobs role en etat running prolonge, risque de desynchronisation scheduler"
  next="reset jobs stale puis relancer planner/backend/frontend"
fi
if [[ "$error_jobs" -ge 3 ]]; then
  verdict="BLOCKED"
  status="BLOCKED"
  blocker_id="CRON_MULTI_ERRORS"
  risks="dégradation multi-jobs, risque de non-livraison MVP"
  next="ouvrir intervention admin immédiate (lock+backup+fix+validation)"
fi
if [[ "$stale_running_jobs" -ge 3 ]]; then
  verdict="BLOCKED"
  status="BLOCKED"
  delta="stale_running_multi"
  blocker_id="CRON_STALE_RUNNING_MULTI"
  risks="plusieurs jobs role sont bloques en running sans progression exploitable"
  next="reset stale jobs en lot puis valider reprise avec runs planner/backend/frontend"
fi
if [[ "$admin_agents_blocked" -eq 1 ]]; then
  verdict="GO_WITH_CAUTION"
  status="IN_PROGRESS"
  delta="admin_agents_attention_signal"
  blocker_id="ADMIN_AGENTS_ATTENTION_REQUIRED"
  risks="admin-agents a remonte un signal de qualite/efficacite"
  next="lire le dernier summary admin-agents, appliquer la next_action puis revalider"
  if [[ "$admin_action_owner_external" -eq 1 ]]; then
    reset_action_stall_counter
    delta="admin_handoff_external_owner"
    blocker_id="ADMIN_HANDOFF_PENDING"
    risks="action en attente de prise en charge par ${admin_agents_action_owner}"
    next="router action admin-agents vers ${admin_agents_action_owner} puis confirmer l'ack dans ADMIN_TEAM_ITERATIONS"
    if [[ -n "$admin_agents_next_action" ]]; then
      next="handoff ${admin_agents_action_owner}: ${admin_agents_next_action}"
    fi
    route_handoff_to_chat "$admin_agents_action_owner" "$admin_agents_issue" "${admin_agents_next_action:-none}" "${admin_agents_action_id:-none}" "${admin_agents_action_scope:-none}"
    admin_action_result="routed"
    admin_action_details="handoff_to_${admin_agents_action_owner}"
    if [[ "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ]]; then
      delta="admin_handoff_external_owner_urgent"
      risks="admin-agents signale un blocage et owner=${admin_agents_action_owner} doit intervenir rapidement"
      blocker_id="ADMIN_HANDOFF_PENDING"
    fi
  else
    action_key="${admin_agents_next_action}|${admin_agents_issue}"
    admin_action_repeat="$(update_action_stall_counter "$action_key")"
    if [[ ! "$admin_action_repeat" =~ ^[0-9]+$ ]]; then
      admin_action_repeat=1
    fi
    if [[ -n "$admin_agents_next_action" ]]; then
      next="appliquer next_action admin-agents: ${admin_agents_next_action}"
    fi
    if [[ "$AUTO_EXEC_ENABLED" == "1" && -n "$admin_agents_next_action" && "$admin_agents_action_owner" == "adminapp-codex" ]]; then
      cooldown_exempt=0
      if [[ "$admin_agents_next_action" == reset_stale_running_role_jobs* ]]; then
        cooldown_exempt=1
      fi
      if [[ "$cooldown_exempt" -eq 0 ]]; then
        if action_cooldown_active "$admin_agents_next_action"; then
          admin_action_result="cooldown"
          admin_action_details="skip_recently_executed"
        else
          execute_admin_action "$admin_agents_next_action"
          admin_action_result="$ACTION_EXEC_RESULT"
          admin_action_details="$ACTION_EXEC_DETAILS"
          mark_action_executed_now "$admin_agents_next_action"
          if [[ "$admin_action_result" == "done" ]]; then
            next="auto_exec_done:${admin_agents_next_action}; attendre recheck admin-agents"
          elif [[ "$admin_action_result" == "failed" ]]; then
            next="auto_exec_failed:${admin_agents_next_action}; recheck puis escalade si repetition"
          elif [[ "$admin_action_result" == "unsupported" ]]; then
            next="auto_exec_unsupported:${admin_agents_next_action}; intervention manuelle adminapp"
          fi
        fi
      else
        execute_admin_action "$admin_agents_next_action"
        admin_action_result="$ACTION_EXEC_RESULT"
        admin_action_details="$ACTION_EXEC_DETAILS"
        mark_action_executed_now "$admin_agents_next_action"
        if [[ "$admin_action_result" == "done" ]]; then
          next="auto_exec_done:${admin_agents_next_action}; attendre recheck admin-agents"
        elif [[ "$admin_action_result" == "failed" ]]; then
          next="auto_exec_failed:${admin_agents_next_action}; recheck puis escalade si repetition"
        elif [[ "$admin_action_result" == "unsupported" ]]; then
          next="auto_exec_unsupported:${admin_agents_next_action}; intervention manuelle adminapp"
        fi
      fi
    fi
    if [[ "$admin_agents_signal_status" == "BLOCKED" || "$admin_agents_signal_status" == "ERROR" ]]; then
      delta="admin_agents_blocked_signal"
      blocker_id="ADMIN_AGENTS_NO_DELIVERY_EVIDENCE"
      risks="admin-agents signale absence de preuve de livraison"
      next="forcer une action admin-agents avec preuve (chat+iterations), puis revalider"
      if [[ -n "$admin_agents_next_action" ]]; then
        next="admin-agents blocked, appliquer next_action: ${admin_agents_next_action}"
      fi
    fi
    if [[ "$admin_action_repeat" -ge 2 && "$admin_action_result" != "done" ]]; then
      verdict="BLOCKED"
      status="BLOCKED"
      delta="admin_agents_action_stalled"
      blocker_id="ADMIN_AGENTS_ACTION_REPEAT_2_TICKS"
      risks="meme issue/action remontee par admin-agents sur >=2 ticks consecutifs"
      next="escalade manuelle immediate: executer ${admin_agents_next_action:-action_inconnue} puis journaliser preuve de resolution"
    fi
  fi
else
  reset_action_stall_counter
fi

ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"
tmux_line="[adminapp-codex-cron ${ts_local}] jobs=${total_jobs} ok=${ok_jobs} running=${running_jobs} pending=${pending_jobs} error=${error_jobs} timeouts=${timeout_jobs} unhealthy=${unhealthy_compact}"
tmux send-keys -t "${SESSION}:${WINDOW}" "printf '%s\n' \"$tmux_line\"" C-m

alert_fingerprint="${verdict}|errors=${error_jobs}|timeouts=${timeout_jobs}|unhealthy=${unhealthy_compact}"
last_alert=""
if [[ -f "$LAST_ALERT_FILE" ]]; then
  last_alert="$(cat "$LAST_ALERT_FILE" 2>/dev/null || true)"
fi
if [[ "$verdict" != "PASS" && "$alert_fingerprint" != "$last_alert" && -f "$CHAT_FILE" ]]; then
  printf -- "- [%s] [adminapp-codex] TYPE: INFO MSG: cron monitor tick => verdict=%s, errors=%s, timeouts=%s, unhealthy=%s. NEXT: %s.\n" \
    "$ts_local" "$verdict" "$error_jobs" "$timeout_jobs" "$unhealthy_compact" "$next" >> "$CHAT_FILE"
fi
printf '%s\n' "$alert_fingerprint" > "$LAST_ALERT_FILE"

echo "STATUS: ${status}"
echo "DELTA: ${delta}"
echo "EVIDENCE: jobs_total=${total_jobs}; ok=${ok_jobs}; running=${running_jobs}; pending=${pending_jobs}; error=${error_jobs}; timed_out=${timeout_jobs}; stale_running=${stale_running_jobs}; stale_running_skipped_live=${stale_running_skipped_live}; unhealthy=${unhealthy_compact}; queue_ready=${queue_ready_items}; admin_signal_status=${admin_agents_signal_status:-none}; admin_issue=${admin_agents_issue:-none}; admin_issue_benign_no_ready=${admin_issue_benign_when_no_ready}; admin_action_id=${admin_agents_action_id:-none}; admin_action_owner=${admin_agents_action_owner:-none}; admin_action_scope=${admin_agents_action_scope:-none}; admin_action_owner_external=${admin_action_owner_external}; admin_action_result=${admin_action_result}; admin_action_details=${admin_action_details}; admin_action_repeat=${admin_action_repeat}"
echo "RISKS: ${risks}"
echo "NEXT: ${next}"
echo "VERDICT: ${verdict}"
echo "BLOCKER_ID: ${blocker_id}"
echo "NEXT_ACTION_UNIQUE: ADMINAPP_CRON_TICK_$(date +%Y%m%d%H%M%S)"
