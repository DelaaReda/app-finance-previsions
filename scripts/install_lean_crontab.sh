#!/usr/bin/env bash
# =============================================================================
# install_lean_crontab.sh — Installe/met à jour les cron jobs du projet
#
# IDEMPOTENT: retire uniquement les lignes marquées [finance-copilot] puis
# réinsère les nouvelles. Tous les autres jobs (ACLED, etc.) sont préservés.
#
# Usage:
#   bash scripts/install_lean_crontab.sh           # installe / met à jour
#   bash scripts/install_lean_crontab.sh --dry-run # preview sans appliquer
#   bash scripts/install_lean_crontab.sh --remove  # retire uniquement
# =============================================================================
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
cd "$ROOT"

MARKER="# [finance-copilot]"
LOG_DIR="$ROOT/logs-codex-runs"
ADMIN_CRON_EXPR="${FC_ADMIN_CRON_EXPR:-*/5}"
DRY_RUN=0; REMOVE_ONLY=0
for arg in "$@"; do
  case "$arg" in --dry-run) DRY_RUN=1;; --remove) REMOVE_ONLY=1;; esac
done

log() { printf '[install_lean_crontab] %s\n' "$*"; }

# Guard: bon projet?
[[ -f "$ROOT/platform/config/lm_used_model_config.sh" ]] || {
  echo "ERREUR: ROOT=$ROOT ne contient pas lm_used_model_config.sh" >&2; exit 1; }

# Nouvelles entrées du projet
build_crons() {
  local bash_bin; bash_bin="$(command -v bash)"
  mkdir -p "$LOG_DIR/fc-ticks"
  cat <<CRONS
${MARKER} vm_resume_guard — réveil VM, kill sessions stales
*/2 * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/vm_resume_guard.sh' >> ${LOG_DIR}/vm-resume.log 2>&1

${MARKER} auto_recover_tmux_roles — maintient sessions tmux en vie
*/10 * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/auto_recover_tmux_roles.sh' >> ${LOG_DIR}/role-recovery.log 2>&1

${MARKER} watchdog_chromium — élimine zombies Chromium
*/15 * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/watchdog_chromium.sh' >> ${LOG_DIR}/watchdog_chromium.log 2>&1

${MARKER} monitor_stack_guard — garde monitor API+tunnel UP
*/1 * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/monitor_stack_guard.sh' >> ${LOG_DIR}/monitor-guard.cron.log 2>&1

${MARKER} log_cleanup — réduction bruit historique (archives)
17 */4 * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/cleanup_monitoring_noise.sh' >> ${LOG_DIR}/log-cleanup.log 2>&1

${MARKER} planner @ :00/:22/:44 — orchestration, dispatch batches
0,22,44 * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh planner' >> ${LOG_DIR}/fc-ticks/planner.cron.log 2>&1

${MARKER} dev @ :06/:28/:50 — code + tests + QA
6,28,50 * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh dev' >> ${LOG_DIR}/fc-ticks/dev.cron.log 2>&1

${MARKER} admin @ ${ADMIN_CRON_EXPR} — santé système, déblocage
${ADMIN_CRON_EXPR} * * * * ${bash_bin} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh admin' >> ${LOG_DIR}/fc-ticks/admin.cron.log 2>&1
CRONS
}

# Retirer les entrées du projet (marqueur + ligne suivante)
strip_crons() {
  printf '%s\n' "$1" | awk -v m="$MARKER" '
    index($0, m) { skip=1; next }
    skip { skip=0; next }
    { print }
  ' \
  | grep -Ev 'scripts/(vm_resume_guard|auto_recover_tmux_roles|watchdog_chromium|monitor_stack_guard|cleanup_monitoring_noise|fc_agent_tick)\.sh' \
  | cat -s  # cat -s collapse les lignes vides multiples
}

CURRENT="$(crontab -l 2>/dev/null || true)"
STRIPPED="$(strip_crons "$CURRENT")"
EXISTING_COUNT="$(printf '%s\n' "$CURRENT" | grep -Ec '(\[finance-copilot\]|scripts/(vm_resume_guard|auto_recover_tmux_roles|watchdog_chromium|monitor_stack_guard|cleanup_monitoring_noise|fc_agent_tick)\.sh)' 2>/dev/null || true)"
[[ -n "$EXISTING_COUNT" ]] || EXISTING_COUNT=0
log "Entrées projet existantes: $EXISTING_COUNT"

if [[ "$REMOVE_ONLY" -eq 1 ]]; then
  [[ "$DRY_RUN" -eq 1 ]] && { log "DRY-RUN: crontab après suppression:"; printf '%s\n' "$STRIPPED"; exit 0; }
  printf '%s\n' "$STRIPPED" | crontab -
  log "✅ Entrées projet supprimées"; exit 0
fi

NEW_ENTRIES="$(build_crons)"
FINAL="$(printf '%s\n\n%s\n' "$STRIPPED" "$NEW_ENTRIES")"

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "=== DRY-RUN: crontab résultant ==="
  printf '%s\n' "$FINAL"
  log "=== Jobs tiers préservés ==="
  printf '%s\n' "$STRIPPED" | grep -v "^#\|^$" || log "  (aucun)"
  exit 0
fi

BACKUP="/tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
printf '%s\n' "$CURRENT" > "$BACKUP"
log "Backup: $BACKUP"
printf '%s\n' "$FINAL" | crontab -
log "✅ Crontab installé (7 entrées projet)"
log "Jobs tiers préservés:"
printf '%s\n' "$STRIPPED" | grep -v "^#\|^$" | sed 's/^/  /' || log "  (aucun)"
