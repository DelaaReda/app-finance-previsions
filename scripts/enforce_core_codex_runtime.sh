#!/usr/bin/env bash
# Enforce codex-only runtime for core roles (planner/dev/admin).
# Usage:
#   bash scripts/enforce_core_codex_runtime.sh           # report only
#   bash scripts/enforce_core_codex_runtime.sh --apply   # stop/disable qwen legacy units + kill qwen tmux sessions
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

ts() { date '+%Y-%m-%dT%H:%M:%S%z'; }
log() { printf '%s [enforce-core-codex] %s\n' "$(ts)" "$*"; }

qwen_sessions() {
  if ! command -v tmux >/dev/null 2>&1; then
    return 0
  fi
  tmux list-sessions -F '#{session_name}' 2>/dev/null \
    | grep -E '^qwen_(planner|dev|admin)_cron$' || true
}

qwen_units=(
  "fc-planner-qwen.timer"
  "fc-dev-qwen.timer"
  "fc-admin-qwen.timer"
  "fc-planner-qwen.service"
  "fc-dev-qwen.service"
  "fc-admin-qwen.service"
)

report_recent_qwen_events() {
  local role=""
  local f=""
  for role in planner dev admin; do
    f="$ROOT/logs-codex-runs/role-runner/${role}.events.log"
    if [[ ! -f "$f" ]]; then
      continue
    fi
    log "recent qwen events role=${role}:"
    rg -n "agent=qwen|session=qwen_" "$f" | tail -n 8 || true
  done
}

log "workspace=${ROOT}"
log "mode=$([[ "$APPLY" -eq 1 ]] && echo apply || echo report)"

log "qwen sessions (core roles):"
SESSIONS="$(qwen_sessions)"
if [[ -n "$SESSIONS" ]]; then
  printf '%s\n' "$SESSIONS" | sed 's/^/  - /'
else
  echo "  - none"
fi

if command -v systemctl >/dev/null 2>&1; then
  log "qwen systemd user units status:"
  for u in "${qwen_units[@]}"; do
    state="$(systemctl --user is-enabled "$u" 2>/dev/null || true)"
    active="$(systemctl --user is-active "$u" 2>/dev/null || true)"
    if [[ -n "$state" || -n "$active" ]]; then
      echo "  - $u enabled=${state:-unknown} active=${active:-unknown}"
    fi
  done
else
  log "systemctl not available (skip unit checks)"
fi

if command -v crontab >/dev/null 2>&1; then
  log "crontab lines mentioning qwen/core runner:"
  (crontab -l 2>/dev/null || true) | rg -n "qwen|cron_tmux_role_runner|fc_agent_tick" || true
fi

report_recent_qwen_events

if [[ "$APPLY" -eq 0 ]]; then
  log "report complete (dry-run). Re-run with --apply to enforce."
  exit 0
fi

if [[ -n "$SESSIONS" ]]; then
  while IFS= read -r s; do
    [[ -n "$s" ]] || continue
    tmux kill-session -t "$s" >/dev/null 2>&1 || true
    log "killed tmux session: $s"
  done <<< "$SESSIONS"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user stop "${qwen_units[@]}" >/dev/null 2>&1 || true
  systemctl --user disable "${qwen_units[@]}" >/dev/null 2>&1 || true
  systemctl --user reset-failed "${qwen_units[@]}" >/dev/null 2>&1 || true
  log "disabled/stopped qwen legacy user units"
fi

log "enforcement done"
