#!/usr/bin/env bash
# MODE: VM_ORCHESTRATION_EC2_APP
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

# 4. Check public app runtime via the canonical AWS wrapper
APP_RUNTIME_STATUS="unknown"
if [[ -x "$ROOT/scripts/aws_remote_app_control.sh" ]]; then
  if APP_RUNTIME_STATUS="$ROOT/scripts/aws_remote_app_control.sh status" 2>&1; then
    log "App runtime status (AWS): ok"
  else
    log "App runtime status (AWS) failed: $APP_RUNTIME_STATUS"
  fi
else
  APP_RUNTIME_STATUS="aws_remote_app_control_missing"
  log "App runtime status skipped: $APP_RUNTIME_STATUS"
fi

log "=== CLEANUP COMPLETE ==="
echo ""
echo "VM wake cleanup done. App runtime status follows canonical AWS control path."
echo "Cron will restart agents at next scheduled tick."
