#!/usr/bin/env bash
# ============================================================
# fc_setup_crons.sh — Configure tous les crons du Finance Copilot
# SAFE: idempotent, supprime les vieux et recrée proprement
# Usage: bash scripts/fc_setup_crons.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_CANDIDATE="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

resolve_root() {
  local candidate="${1:-}"
  local shared="/home/venom/shared/analyse-financiere"
  local vm="/home/venom/analyse-financiere"
  local mac="/Users/venom/Documents/analyse-financiere"
  local path=""
  for path in "$candidate" "$shared" "$vm" "$mac"; do
    if [[ -z "$path" ]]; then
      continue
    fi
    if [[ -d "$path/scripts" ]] && [[ -d "$path/platform" ]]; then
      printf '%s\n' "$path"
      return 0
    fi
  done
  printf '%s\n' "$candidate"
}

workspace_writable() {
  local candidate="${1:-}"
  [[ -n "$candidate" ]] || return 1
  mkdir -p "$candidate/logs-codex-runs" >/dev/null 2>&1 || return 1
  [[ -w "$candidate/logs-codex-runs" ]]
}

ROOT="$(resolve_root "$ROOT_CANDIDATE")"
if ! workspace_writable "$ROOT"; then
  for fallback in "/home/venom/analyse-financiere" "/home/venom/shared/analyse-financiere"; do
    if [[ "$fallback" == "$ROOT" ]]; then
      continue
    fi
    if [[ -d "$fallback/scripts" ]] && [[ -d "$fallback/platform" ]] && workspace_writable "$fallback"; then
      ROOT="$fallback"
      break
    fi
  done
fi
BASH_BIN="$(which bash)"
CRON_PROFILE="${FC_CRON_PROFILE:-full}"
ADMIN_CRON_EXPR="${FC_ADMIN_CRON_EXPR:-*/5}"
ADMIN_PROMPT_TIMEOUT_SECONDS="${FC_ADMIN_PROMPT_TIMEOUT_SECONDS:-300}"
ADMIN_RETRY_TIMEOUT_SECONDS="${FC_ADMIN_RETRY_TIMEOUT_SECONDS:-120}"
ADMIN_TICK_TIMEOUT_SECONDS="${FC_ADMIN_TICK_TIMEOUT_SECONDS:-480}"
ROLE_RECOVERY_LOG_DIR="${FC_ROLE_RECOVERY_LOG_DIR:-${ROOT}/logs-codex-runs}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      CRON_PROFILE="${2:-full}"
      shift 2
      ;;
    --canary)
      CRON_PROFILE="canary"
      shift
      ;;
    --full)
      CRON_PROFILE="full"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: bash scripts/fc_setup_crons.sh [--profile full|canary|--canary|--full]" >&2
      exit 2
      ;;
  esac
done

case "$CRON_PROFILE" in
  full|canary) ;;
  *)
    echo "Invalid profile: $CRON_PROFILE (expected: full|canary)" >&2
    exit 2
    ;;
esac

echo "📋 Configuring Finance Copilot cron jobs..."
echo "   Root: $ROOT"
echo "   Profile: $CRON_PROFILE"
echo ""

# ── Backup existing crontab ───────────────────────────────
crontab -l 2>/dev/null > /tmp/crontab_backup_$(date +%Y%m%d%H%M%S).txt || true
echo "✅ Backed up existing crontab"

# ── Build new crontab ─────────────────────────────────────
CRON_CONTENT=$(crontab -l 2>/dev/null | grep -v "fc_agent_tick\|auto_recover_tmux\|fc_setup\|cron_tmux_role_runner\|vm_resume_guard\|fc_resume\|watchdog_chromium\|cleanup_monitoring_noise" || true)

ROLE_CRON_BLOCK=""
if [[ "$CRON_PROFILE" == "canary" ]]; then
  ROLE_CRON_BLOCK=$(cat <<EOF
# [finance-copilot] PLANNER (lean canary) — cadence réduite
0,30 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh planner' >> ${ROOT}/logs-codex-runs/fc-ticks/planner.cron.log 2>&1

# [finance-copilot] DEV (lean canary) — lane delivery consolidée
10,40 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh dev' >> ${ROOT}/logs-codex-runs/fc-ticks/dev.cron.log 2>&1

# ADMIN — volontairement désactivé en canary
EOF
)
else
  ROLE_CRON_BLOCK=$(cat <<EOF
# [finance-copilot] PLANNER — orchestration et dispatch
0,22,44 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh planner' >> ${ROOT}/logs-codex-runs/fc-ticks/planner.cron.log 2>&1

# [finance-copilot] DEV — lane delivery consolidée (backend/frontend/data/tests)
6,28,50 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh dev' >> ${ROOT}/logs-codex-runs/fc-ticks/dev.cron.log 2>&1

# [finance-copilot] ADMIN — santé runtime, déblocage, hygiene
${ADMIN_CRON_EXPR} * * * * ${BASH_BIN} -lc 'cd ${ROOT} && FC_ADMIN_PROMPT_TIMEOUT_SECONDS=${ADMIN_PROMPT_TIMEOUT_SECONDS} FC_ADMIN_RETRY_TIMEOUT_SECONDS=${ADMIN_RETRY_TIMEOUT_SECONDS} FC_ADMIN_TICK_TIMEOUT_SECONDS=${ADMIN_TICK_TIMEOUT_SECONDS} bash scripts/fc_agent_tick.sh admin' >> ${ROOT}/logs-codex-runs/fc-ticks/admin.cron.log 2>&1
EOF
)
fi

: > /tmp/fc_new_crontab
cat >> /tmp/fc_new_crontab << EOF
${CRON_CONTENT}

# ============================================================
# Finance Copilot Agent Orchestration
# Generated: $(date)
# ============================================================

# [finance-copilot] VM Resume guard — détecte le réveil et tue les sessions stales
*/2 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/vm_resume_guard.sh' >> ${ROOT}/logs-codex-runs/vm-resume.log 2>&1

# [finance-copilot] Auto-recovery sessions (garde les sessions tmux vivantes)
*/10 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && FC_ROLE_RECOVERY_LOG_DIR=${ROLE_RECOVERY_LOG_DIR} bash scripts/auto_recover_tmux_roles.sh' >> ${ROOT}/logs-codex-runs/role-recovery.log 2>&1

# [finance-copilot] Watchdog Chromium zombies + stale runtime locks
*/15 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/watchdog_chromium.sh' >> ${ROOT}/logs-codex-runs/watchdog_chromium.log 2>&1

# [finance-copilot] Runtime logs cleanup (bruit historique + archives)
17 */4 * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/cleanup_monitoring_noise.sh' >> ${ROOT}/logs-codex-runs/log-cleanup.log 2>&1

${ROLE_CRON_BLOCK}

# ============================================================
EOF

crontab /tmp/fc_new_crontab
rm -f /tmp/fc_new_crontab

echo ""
echo "✅ Cron jobs installed!"
echo ""
echo "📅 Schedule:"
echo "   - vm_resume_guard     : every 2 min  (détecte réveil VM)"
echo "   - auto_recover        : every 10 min (garde sessions vivantes)"
echo "   - log_cleanup         : minute 17 every 4h"
if [[ "$CRON_PROFILE" == "canary" ]]; then
  echo "   - planner             : 0,30  (canary)"
  echo "   - dev                 : 10,40 (canary)"
  echo "   - admin               : paused (canary)"
else
  echo "   - planner             : 0,22,44"
  echo "   - dev                 : 6,28,50"
  echo "   - admin               : ${ADMIN_CRON_EXPR}"
fi
echo ""
echo "📋 Current crontab:"
crontab -l 2>/dev/null | grep -v "^#\|^$"
