#!/usr/bin/env bash
# =============================================================================
# setup_lean_team.sh — Initialise/répare les sessions tmux des 3 rôles lean
#
# SAFE: ne kill une session que si prouvablement stale (idle > 10min).
#       Arrêt via C-c + kill-session, jamais kill -9.
#
# Usage:
#   bash scripts/setup_lean_team.sh              # tous les rôles
#   bash scripts/setup_lean_team.sh planner      # un seul rôle
#   bash scripts/setup_lean_team.sh --dry-run
# =============================================================================
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd -P)"
cd "$ROOT"

source platform/config/lm_used_model_config.sh 2>/dev/null || true

STATE_DIR="${TMUX_ROLE_STATE_DIR:-/home/venom/.openclaw/cron/role-state}"
LOG_DIR="$ROOT/logs-codex-runs/fc-ticks"
STALE_IDLE_SECONDS="${LEAN_STALE_IDLE_SECONDS:-600}"
DRY_RUN=0; FILTER_ROLE=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --*) echo "Usage: $0 [role] [--dry-run]" >&2; exit 1 ;;
    *)   FILTER_ROLE="$arg" ;;
  esac
done

ROLES=(planner dev admin)
[[ -n "$FILTER_ROLE" ]] && ROLES=("$FILTER_ROLE")

log()  { printf '[setup_lean_team] %s\n' "$*"; }
dry()  { [[ "$DRY_RUN" -eq 1 ]] && printf '[DRY-RUN] %s\n' "$*" || true; }

# Retourne 0 si la session est stale (safe à tuer), 1 si active
session_is_stale() {
  local session="$1"
  tmux has-session -t "$session" 2>/dev/null || return 0  # absente = stale

  # Pane en cours d'exécution codex/node/qwen → active
  local pane_cmd
  pane_cmd="$(tmux display-message -p -t "${session}:0" '#{pane_current_command}' 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)"
  case "$pane_cmd" in
    codex|node|python|python3|qwen) return 1 ;;
  esac

  # Activité récente sur le tick log
  local role="${session#codex_}"; role="${role%_cron}"
  local trace="$LOG_DIR/${role}.tick.log"
  if [[ -f "$trace" ]]; then
    local age=$(( $(date +%s) - $(stat -c %Y "$trace" 2>/dev/null || echo 0) ))
    [[ "$age" -lt "$STALE_IDLE_SECONDS" ]] && return 1  # récent = active
  fi
  return 0  # stale
}

clear_stale_lock() {
  local lock="$STATE_DIR/${1}.run.lock"
  [[ -f "$lock" ]] || return 0
  local age=$(( $(date +%s) - $(stat -c %Y "$lock" 2>/dev/null || echo 0) ))
  if [[ "$age" -gt 900 ]]; then
    log "  🔓 Lock stale (${age}s) → $lock"
    [[ "$DRY_RUN" -eq 0 ]] && rm -f "$lock" || dry "rm -f $lock"
  fi
}

ensure_session() {
  local role="$1"
  local session="codex_${role}_cron"
  if ! tmux has-session -t "$session" 2>/dev/null; then
    log "  ✨ Création session: $session"
    [[ "$DRY_RUN" -eq 0 ]] || { dry "tmux new-session -d -s $session"; return; }
    tmux new-session -d -s "$session" -x 220 -y 50 2>/dev/null || true
    tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  else
    log "  ✅ Session présente: $session"
  fi
}

log "Rôles: ${ROLES[*]} | dry=$DRY_RUN | stale_threshold=${STALE_IDLE_SECONDS}s"
mkdir -p "$STATE_DIR" "$LOG_DIR"

for role in "${ROLES[@]}"; do
  log "--- $role ---"
  clear_stale_lock "$role"
  session="codex_${role}_cron"

  if tmux has-session -t "$session" 2>/dev/null && session_is_stale "$session"; then
    log "  ⚠️  Stale → arrêt propre: $session"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      tmux send-keys -t "${session}:0" C-c 2>/dev/null || true
      sleep 1
      tmux kill-session -t "$session" 2>/dev/null || true
    else
      dry "tmux kill-session -t $session"
    fi
  fi

  ensure_session "$role"
done

log "✅ Terminé"
