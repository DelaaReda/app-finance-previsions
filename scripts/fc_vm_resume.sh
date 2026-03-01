#!/usr/bin/env bash
# ============================================================
# fc_vm_resume.sh — Post-sleep recovery rapide
# Remplace vm_resume_guard.sh (corrige le chemin hardcodé ~/analyse-financiere)
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="/tmp/fc_vm_resume_last"
GAP_THRESHOLD=300  # 5 minutes = probablement un sleep

NOW=$(date +%s)
LAST=0
[[ -f "$STATE_FILE" ]] && LAST=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
echo "$NOW" > "$STATE_FILE"

GAP=$((NOW - LAST))

if [[ "$LAST" -eq 0 || "$GAP" -lt "$GAP_THRESHOLD" ]]; then
  # Normal tick — rien à faire
  exit 0
fi

echo "$(date '+%Y-%m-%dT%H:%M:%S') [VM_RESUME] Gap=${GAP}s detected, running recovery..." | tee -a "$ROOT/logs-codex-runs/vm-resume.log"

# Tuer toutes les sessions agent stales
ACTIVE_ROLES=("planner" "backend_engineer" "frontend_engineer" "data_analyst")
for role in "${ACTIVE_ROLES[@]}"; do
  SESSION="codex_${role}_cron"
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    # Vérifier si codex est bloqué (rate limit dialog, etc.)
    PANE_TEXT=$(tmux capture-pane -pt "$SESSION:0.0" -S -10 2>/dev/null || echo "")
    if echo "$PANE_TEXT" | grep -q "press enter\|rate limit\|Press enter"; then
      echo "$(date '+%H:%M:%S') [RESUME] Killing stuck session $SESSION (rate limit dialog)" | tee -a "$ROOT/logs-codex-runs/vm-resume.log"
      tmux kill-session -t "$SESSION" 2>/dev/null || true
    else
      echo "$(date '+%H:%M:%S') [RESUME] Session $SESSION seems OK, keeping" | tee -a "$ROOT/logs-codex-runs/vm-resume.log"
    fi
  fi
done

# Reset rate limit cache pour les roles
RATE_CACHE_DIR="/home/venom/.openclaw/cron/role-state"
if [[ -d "$RATE_CACHE_DIR" ]]; then
  find "$RATE_CACHE_DIR" -name "*.rate_limit*" -delete 2>/dev/null || true
  echo "$(date '+%H:%M:%S') [RESUME] Rate limit cache cleared" | tee -a "$ROOT/logs-codex-runs/vm-resume.log"
fi

# Clear tick resume files so next tick doesn't think it's too fast
rm -f /tmp/fc_last_tick_* 2>/dev/null || true

echo "$(date '+%Y-%m-%dT%H:%M:%S') [VM_RESUME] Recovery complete" | tee -a "$ROOT/logs-codex-runs/vm-resume.log"
