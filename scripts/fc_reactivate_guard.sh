#!/usr/bin/env bash
# ============================================================
# fc_reactivate_guard.sh — Reactivation + post-checks agents
# Usage:
#   bash scripts/fc_reactivate_guard.sh
#   bash scripts/fc_reactivate_guard.sh --kick-planner
#   bash scripts/fc_reactivate_guard.sh --audit-only
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTIVE_ROLES_FULL=("planner" "dev" "admin")
ACTIVE_ROLES_CANARY=("planner" "dev")
ACTIVE_ROLES=("${ACTIVE_ROLES_FULL[@]}")
KICK_PLANNER=0
AUDIT_ONLY=0
CRON_PROFILE="${FC_CRON_PROFILE:-full}"

for arg in "$@"; do
  case "$arg" in
    --kick-planner) KICK_PLANNER=1 ;;
    --audit-only) AUDIT_ONLY=1 ;;
    --canary) CRON_PROFILE="canary" ;;
    --full) CRON_PROFILE="full" ;;
    *)
      echo "[reactivate_guard] unknown option: $arg" >&2
      echo "Usage: bash scripts/fc_reactivate_guard.sh [--kick-planner] [--audit-only] [--canary|--full]" >&2
      exit 2
      ;;
  esac
done

case "$CRON_PROFILE" in
  canary) ACTIVE_ROLES=("${ACTIVE_ROLES_CANARY[@]}") ;;
  full) ACTIVE_ROLES=("${ACTIVE_ROLES_FULL[@]}") ;;
  *)
    echo "[reactivate_guard] invalid CRON_PROFILE=$CRON_PROFILE (expected full|canary)" >&2
    exit 2
    ;;
esac

ok()   { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*" >&2; }

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || { fail "missing command: $cmd"; exit 2; }
}

role_session() {
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    dev) echo "codex_dev_cron" ;;
    admin) echo "codex_admin_cron" ;;
    *) return 1 ;;
  esac
}

cleanup_stale_locks() {
  local shared_dir="$ROOT/.tmp/openclaw-shared-locks"
  local role_state_dir="$HOME/.openclaw/cron/role-state"
  local stale_shared=0
  local stale_run=0
  local stale_fc=0
  if [[ -d "$shared_dir" ]]; then
    stale_shared="$(find "$shared_dir" -name '*.lock' -mmin +30 | wc -l | tr -d ' ')"
    find "$shared_dir" -name '*.lock' -mmin +30 -delete 2>/dev/null || true
  fi
  if [[ -d "$role_state_dir" ]]; then
    stale_run="$(find "$role_state_dir" -name '*.run.lock' -mmin +20 | wc -l | tr -d ' ')"
    find "$role_state_dir" -name '*.run.lock' -mmin +20 -delete 2>/dev/null || true
  fi
  stale_fc="$(find /tmp/fc-agent-locks -name '*.lock' -mmin +20 2>/dev/null | wc -l | tr -d ' ')"
  find /tmp/fc-agent-locks -name '*.lock' -mmin +20 -delete 2>/dev/null || true
  ok "stale locks cleaned: shared=${stale_shared:-0} role_state=${stale_run:-0} fc=${stale_fc:-0}"
}

cleanup_stale_chromium() {
  local stale_pids=""
  stale_pids="$(ps -eo pid=,etimes=,comm=,args= | awk '
    {
      pid=$1; et=$2; cmd=$3; $1=""; $2=""; $3="";
      args=$0;
      if (et+0 < 3600) next;
      if (cmd !~ /(chromium|chrome)/) next;
      if (args ~ /(renderer|zygote|gpu-process|utility|headless)/) print pid;
    }' | tr '\n' ' ')"
  if [[ -n "${stale_pids// }" ]]; then
    # shellcheck disable=SC2086
    kill $stale_pids 2>/dev/null || true
    ok "killed stale chromium pids: ${stale_pids}"
  else
    ok "no stale chromium workers detected"
  fi
}

audit_snapshot() {
  local cron_count legacy_cron_count session_up=0 session=""
  cron_count="$(
    (crontab -l 2>/dev/null || true) \
      | { grep -E 'fc_agent_tick\.sh (planner|dev|admin)' || true; } \
      | { grep -Ev '^[[:space:]]*#' || true; } \
      | wc -l | tr -d ' '
  )"
  legacy_cron_count="$(
    (crontab -l 2>/dev/null || true) \
      | { grep -E 'fc_agent_tick\.sh (backend_engineer|frontend_engineer|data_analyst|integrator|analyst|architect|po|scrum_master|qa|tester|infra_engineer|clawsentinel)' || true; } \
      | { grep -Ev '^[[:space:]]*#' || true; } \
      | wc -l | tr -d ' '
  )"
  for role in "${ACTIVE_ROLES[@]}"; do
    session="$(role_session "$role")"
    if tmux has-session -t "$session" 2>/dev/null; then
      session_up=$((session_up+1))
    fi
  done
  ok "audit snapshot: profile=${CRON_PROFILE} cron_tick_jobs=${cron_count:-0} legacy_tick_jobs=${legacy_cron_count:-0} active_sessions=${session_up}/${#ACTIVE_ROLES[@]}"
}

require_cmd bash
require_cmd tmux
require_cmd crontab

cd "$ROOT"

ok "preflight cleanup"
cleanup_stale_locks
cleanup_stale_chromium
if [[ -x "scripts/cleanup_monitoring_noise.sh" ]]; then
  ok "cleanup monitoring noise"
  bash scripts/cleanup_monitoring_noise.sh >/tmp/fc_reactivate_log_cleanup.out 2>/tmp/fc_reactivate_log_cleanup.err || {
    warn "cleanup_monitoring_noise failed (continuing)"
    sed -n '1,60p' /tmp/fc_reactivate_log_cleanup.err >&2 || true
  }
fi
audit_snapshot

if [[ "$AUDIT_ONLY" -eq 1 ]]; then
  ok "audit-only mode: no cron/session activation performed"
  exit 0
fi

ok "install/reinstall cron jobs"
bash scripts/fc_setup_crons.sh --profile "$CRON_PROFILE" >/tmp/fc_reactivate_setup.out 2>/tmp/fc_reactivate_setup.err || {
  fail "fc_setup_crons failed"
  sed -n '1,80p' /tmp/fc_reactivate_setup.err >&2 || true
  exit 1
}

ok "start/recover tmux role sessions"
bash scripts/auto_recover_tmux_roles.sh >/tmp/fc_reactivate_recover.out 2>/tmp/fc_reactivate_recover.err || {
  fail "auto_recover_tmux_roles failed"
  sed -n '1,120p' /tmp/fc_reactivate_recover.err >&2 || true
  exit 1
}

if [[ "$CRON_PROFILE" == "canary" ]]; then
  expected_cron_count=2
else
  expected_cron_count=3
fi
cron_count="$(
  (crontab -l 2>/dev/null || true) \
    | { grep -E 'fc_agent_tick\.sh (planner|dev|admin)' || true; } \
    | { grep -Ev '^[[:space:]]*#' || true; } \
    | wc -l | tr -d ' '
)"
if [[ "${cron_count:-0}" -lt "$expected_cron_count" ]]; then
  fail "expected >=${expected_cron_count} agent tick jobs in crontab (profile=${CRON_PROFILE}), got ${cron_count:-0}"
  exit 1
fi
ok "crontab has ${cron_count} agent tick jobs (profile=${CRON_PROFILE})"

legacy_cron_count="$(
  (crontab -l 2>/dev/null || true) \
    | { grep -E 'fc_agent_tick\.sh (backend_engineer|frontend_engineer|data_analyst|integrator|analyst|architect|po|scrum_master|qa|tester|infra_engineer|clawsentinel)' || true; } \
    | { grep -Ev '^[[:space:]]*#' || true; } \
    | wc -l | tr -d ' '
)"
if [[ "${legacy_cron_count:-0}" -gt 0 ]]; then
  fail "legacy role tick jobs still present in crontab: ${legacy_cron_count}"
  (crontab -l 2>/dev/null || true) | grep -E 'fc_agent_tick\.sh (backend_engineer|frontend_engineer|data_analyst|integrator|analyst|architect|po|scrum_master|qa|tester|infra_engineer|clawsentinel)' | sed 's/^/[legacy] /' >&2 || true
  exit 1
fi
ok "no legacy role tick jobs in crontab"

missing_sessions=()
for role in "${ACTIVE_ROLES[@]}"; do
  session="$(role_session "$role")"
  if tmux has-session -t "$session" 2>/dev/null; then
    ok "session up: $session"
  else
    missing_sessions+=("$session")
  fi
done

if [[ "${#missing_sessions[@]}" -gt 0 ]]; then
  warn "sessions missing after first recovery: ${missing_sessions[*]}"
  ok "retry recovery once"
  bash scripts/auto_recover_tmux_roles.sh >/tmp/fc_reactivate_recover_retry.out 2>/tmp/fc_reactivate_recover_retry.err || true

  still_missing=()
  for session in "${missing_sessions[@]}"; do
    if ! tmux has-session -t "$session" 2>/dev/null; then
      still_missing+=("$session")
    fi
  done
  if [[ "${#still_missing[@]}" -gt 0 ]]; then
    fail "sessions still missing: ${still_missing[*]}"
    exit 1
  fi
fi

if [[ "$KICK_PLANNER" -eq 1 ]]; then
  ok "kick planner tick (bounded timeout)"
  timeout 120 bash scripts/fc_agent_tick.sh planner >/tmp/fc_reactivate_kick.out 2>/tmp/fc_reactivate_kick.err || true
  tail -n 5 /tmp/fc_reactivate_kick.err 2>/dev/null || true
fi

MCP_LOG="${HOME}/.config/Claude/logs/main.log"
if [[ -f "$MCP_LOG" ]]; then
  if tail -n 600 "$MCP_LOG" | grep -Eq 'Launching MCP Server: (filesystem|filesystem-root|project-shell)'; then
    ok "Claude MCP launch traces detected"
  else
    warn "no recent MCP launch trace for filesystem/project-shell; restart Claude Desktop if needed"
  fi
else
  warn "Claude main.log not found at $MCP_LOG"
fi

ok "final health check"
bash scripts/fc_health_check.sh

ok "reactivation guard finished successfully"
