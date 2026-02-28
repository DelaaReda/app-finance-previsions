#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$WORKDIR"

TS="$(date +%Y%m%d-%H%M%S)"
HANDOFF="docs/ops/TMUX_HANDOFF_clawsentinel_${TS}.md"
MODEL="$(openclaw config get agents.defaults.model.primary 2>/dev/null || echo unknown)"
THINKING="$(openclaw config get agents.defaults.thinkingDefault 2>/dev/null || echo unknown)"

{
  echo "# TMUX Session Handoff"
  echo
  echo "- generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- role: clawsentinel"
  echo "- responsibility: safety/quality owner"
  echo "- workspace: ${WORKDIR}"
  echo
  echo "## Main Agent"
  echo "- model: ${MODEL}"
  echo "- reasoning: ${THINKING}"
  echo
  echo "## Cron Snapshot"
} > "$HANDOFF"

openclaw cron list --json \
  | jq -r '.jobs[] | "- \(.name): status=\(.state.lastStatus) everyMs=\(.schedule.everyMs) thinking=\(.payload.thinking)"' \
  >> "$HANDOFF"

{
  echo
  echo "## Recent Tri-Admin Chat"
  tail -n 20 docs/ops/ADMIN_TEAM_CHAT.md
  echo
  echo "## Recent Tri-Admin Iterations"
  tail -n 30 docs/ops/ADMIN_TEAM_ITERATIONS.md
  echo
  echo "## Active Focus"
  echo "- objective: improve cron delivery quality and reduce stale blockers/NO_DELTA"
  echo "- rule: one runtime variable per intervention + lock/backup/force-run + journal"
} >> "$HANDOFF"

SESSION="clawsentinel-sync-$(date +%H%M)"
tmux new-session -d -s "$SESSION" -c "$WORKDIR"
tmux set-option -t "$SESSION" history-limit 200000 >/dev/null 2>&1 || true

tmux send-keys -t "$SESSION:0.0" "export ADMIN_ROLE=clawsentinel" C-m
tmux send-keys -t "$SESSION:0.0" "export ADMIN_RESPONSIBILITY=safety-quality" C-m
tmux send-keys -t "$SESSION:0.0" "clear" C-m
tmux send-keys -t "$SESSION:0.0" "printf '[ROLE] clawsentinel\n[RESPONSIBILITY] safety/quality owner\n[WORKSPACE] ${WORKDIR}\n\n'" C-m
tmux send-keys -t "$SESSION:0.0" "cat '$HANDOFF'" C-m
tmux send-keys -t "$SESSION:0.0" "echo" C-m
tmux send-keys -t "$SESSION:0.0" "echo '[READY] Session active. Attach: tmux attach -t $SESSION'" C-m

echo "session=$SESSION"
echo "handoff=$HANDOFF"
tmux capture-pane -p -S -40 -t "$SESSION:0.0" | tail -n 14
