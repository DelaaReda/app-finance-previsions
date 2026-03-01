#!/usr/bin/env bash
# ============================================================
# vm_wake_cleanup.sh — Nettoyage propre après réveil VM
# Détecte le réveil (gap > 5 min), kill les zombies, relance
# Usage: bash scripts/vm_wake_cleanup.sh [--force]
# ============================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="/tmp/.vm_wake_last_epoch"
FORCE="${1:-}"
LOG="$ROOT/logs-codex-runs/vm-wake.log"
mkdir -p "$(dirname "$LOG")"

ts() { date '+%Y-%m-%dT%H:%M:%S'; }
log() { echo "$(ts) $*" | tee -a "$LOG"; }

NOW=$(date +%s)
LAST=0
[[ -f "$STATE_FILE" ]] && LAST=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
echo "$NOW" > "$STATE_FILE"

GAP=$((NOW - LAST))
IS_RESUME=0
[[ "$LAST" -gt 0 && "$GAP" -gt 300 ]] && IS_RESUME=1
[[ "$FORCE" == "--force" ]] && IS_RESUME=1

if [[ "$IS_RESUME" -eq 0 ]]; then
  exit 0
fi

log "=== VM WAKE DETECTED (gap=${GAP}s) ==="

# 1. Kill all stale codex sessions
log "Killing stale tmux agent sessions..."
for session in codex_planner_cron codex_frontend_engineer_cron codex_backend_engineer_cron codex_data_analyst_cron; do
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session" 2>/dev/null && log "  killed: $session" || true
  fi
done

# 2. Kill orphan codex processes
log "Killing orphan codex processes..."
KILLED=0
while IFS= read -r pid; do
  kill -9 "$pid" 2>/dev/null && KILLED=$((KILLED+1)) || true
done < <(pgrep -f "codex --no-alt-screen|bin/codex$" 2>/dev/null || true)
log "  killed $KILLED orphan procs"

# 3. Clear stale locks
log "Clearing locks..."
rm -f /tmp/fc-agent-locks/*.lock 2>/dev/null || true
rm -f /tmp/fc_last_tick_* 2>/dev/null || true
rm -f "$ROOT"/.tmp/openclaw-shared-locks/*.lock 2>/dev/null || true

# 4. Check backend + frontend still up
BACKEND_OK=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8050/api/health" 2>/dev/null || echo "000")
FRONTEND_OK=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173/" 2>/dev/null || echo "000")
log "Services: backend=$BACKEND_OK frontend=$FRONTEND_OK"

# 5. Restart backend if down
if [[ "$BACKEND_OK" != "200" ]]; then
  log "Backend DOWN — attempting restart..."
  cd "$ROOT"
  tmux new-session -d -s "finance_backend" "bash -lc 'cd $ROOT && python3 apps/api/src/main.py 2>&1 | tee logs/backend.log'" 2>/dev/null || true
  sleep 5
  BACKEND_OK=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8050/api/health" 2>/dev/null || echo "000")
  log "Backend after restart: $BACKEND_OK"
fi

# 6. Restart frontend if down
if [[ "$FRONTEND_OK" != "200" ]]; then
  log "Frontend DOWN — attempting restart..."
  PAGES_DIR="$ROOT/apps/web/src/domains/forecasts/pages"
  tmux new-session -d -s "finance_frontend" "bash -lc 'cd $PAGES_DIR && python3 -m http.server 5173 2>&1 | tee $ROOT/logs/frontend.log'" 2>/dev/null || true
  sleep 2
  log "Frontend restarted"
fi

log "=== CLEANUP COMPLETE ==="
echo ""
echo "VM wake cleanup done. Services: backend=$BACKEND_OK frontend=$FRONTEND_OK"
echo "Cron will restart agents at next scheduled tick."
