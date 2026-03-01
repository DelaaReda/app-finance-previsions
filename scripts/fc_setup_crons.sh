#!/usr/bin/env bash
# ============================================================
# fc_setup_crons.sh — Configure tous les crons du Finance Copilot
# SAFE: idempotent, supprime les vieux et recrée proprement
# Usage: bash scripts/fc_setup_crons.sh
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASH_BIN="$(which bash)"

echo "📋 Configuring Finance Copilot cron jobs..."
echo "   Root: $ROOT"
echo ""

# ── Backup existing crontab ───────────────────────────────
crontab -l 2>/dev/null > /tmp/crontab_backup_$(date +%Y%m%d%H%M%S).txt || true
echo "✅ Backed up existing crontab"

# ── Build new crontab ─────────────────────────────────────
CRON_CONTENT=$(crontab -l 2>/dev/null | grep -v "fc_agent_tick\|auto_recover_tmux\|fc_setup\|cron_tmux_role_runner\|vm_resume_guard\|fc_resume" || true)

cat >> /tmp/fc_new_crontab << EOF
${CRON_CONTENT}

# ============================================================
# Finance Copilot Agent Orchestration
# Generated: $(date)
# ============================================================

# VM Resume guard — détecte le réveil et tue les sessions stales
*/2 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/vm_resume_guard.sh' >> ${ROOT}/logs-codex-runs/vm-resume.log 2>&1

# Auto-recovery sessions (garde les sessions tmux vivantes)
*/10 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/auto_recover_tmux_roles.sh' >> ${ROOT}/logs-codex-runs/role-recovery.log 2>&1

# PLANNER — toutes les 15 minutes (orchestrateur central)
*/15 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh planner' >> ${ROOT}/logs-codex-runs/fc-ticks/planner.cron.log 2>&1

# BACKEND_ENGINEER — toutes les 20 minutes
*/20 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh backend_engineer' >> ${ROOT}/logs-codex-runs/fc-ticks/backend_engineer.cron.log 2>&1

# FRONTEND_ENGINEER — toutes les 20 minutes (offset 7min)
7-59/20 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh frontend_engineer' >> ${ROOT}/logs-codex-runs/fc-ticks/frontend_engineer.cron.log 2>&1

# DATA_ANALYST — toutes les 30 minutes (offset 12min)
12-59/30 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/fc_agent_tick.sh data_analyst' >> ${ROOT}/logs-codex-runs/fc-ticks/data_analyst.cron.log 2>&1

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
echo "   - planner             : every 15 min (orchestrateur)"
echo "   - backend_engineer    : every 20 min"
echo "   - frontend_engineer   : every 20 min (offset 7min)"
echo "   - data_analyst        : every 30 min (offset 12min)"
echo ""
echo "📋 Current crontab:"
crontab -l 2>/dev/null | grep -v "^#\|^$"
