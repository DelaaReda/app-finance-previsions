#!/usr/bin/env bash
# ============================================================
# fc_agent_tick.sh — Lance un tick d'agent via cron_tmux_role_runner
# Usage: fc_agent_tick.sh <role>
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROLE="${1:-}"
LOG_DIR="$ROOT/logs-codex-runs/fc-ticks"
LOCK_DIR="/tmp/fc-agent-locks"

mkdir -p "$LOG_DIR" "$LOCK_DIR"

if [[ -z "$ROLE" ]]; then
  echo "Usage: $0 <role>" >&2
  exit 1
fi

# Only run these 4 active roles
case "$ROLE" in
  planner|backend_engineer|frontend_engineer|data_analyst) ;;
  *)
    echo "[fc_tick] Role '$ROLE' not in active set, skipping" >&2
    exit 0
    ;;
esac

LOCK="$LOCK_DIR/$ROLE.lock"
LOG="$LOG_DIR/$ROLE.tick.log"

# Prevent overlap
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[fc_tick] $ROLE already running, skip" >> "$LOG"
  exit 0
fi

ts() { date '+%Y-%m-%dT%H:%M:%S'; }

echo "" >> "$LOG"
echo "$(ts) [START] role=$ROLE" >> "$LOG"

# --- VM Resume detection ---
RESUME_FILE="/tmp/fc_last_tick_$ROLE"
NOW_EPOCH="$(date +%s)"
LAST_EPOCH=0
[[ -f "$RESUME_FILE" ]] && LAST_EPOCH="$(cat "$RESUME_FILE" 2>/dev/null || echo 0)"
echo "$NOW_EPOCH" > "$RESUME_FILE"

GAP=$((NOW_EPOCH - LAST_EPOCH))
SESSION="codex_${ROLE}_cron"
[[ "$ROLE" == "planner" ]] && SESSION="codex_planner_cron"

# If gap > 10 min, VM likely woke from sleep — kill stale session
if [[ "$LAST_EPOCH" -gt 0 && "$GAP" -gt 600 ]]; then
  echo "$(ts) [RESUME] gap=${GAP}s, killing stale session $SESSION" >> "$LOG"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  sleep 1
fi

# --- Ensure tmux session exists with codex ---
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "$(ts) [START_SESSION] $SESSION" >> "$LOG"
  tmux new-session -d -s "$SESSION" -c "$ROOT" \
    "bash -lc 'unset NO_COLOR; export TERM=xterm-256color FORCE_COLOR=1; exec codex --no-alt-screen'"
  sleep 3
fi

# --- Run the role tick ---
echo "$(ts) [TICK] launching cron_tmux_role_runner.sh $ROLE" >> "$LOG"

cd "$ROOT"
source platform/config/lm_used_model_config.sh 2>/dev/null || true

RESULT=$(timeout 900 bash scripts/cron_tmux_role_runner.sh "$ROLE" 2>&1 || true)
RC=$?

echo "$(ts) [END] role=$ROLE rc=$RC" >> "$LOG"
echo "$RESULT" >> "$LOG"

exit $RC
