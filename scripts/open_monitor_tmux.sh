#!/usr/bin/env bash
# open_monitor_tmux.sh — Ouvre (ou réattache) le dashboard monitoring dans tmux
# Usage: bash scripts/open_monitor_tmux.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SESSION="tmux_live_monitor"
WINDOW="monitor"

# Si la session existe déjà, kill et recréer (refresh propre)
if tmux has-session -t "$SESSION" 2>/dev/null; then
  # Vérifier si le pane tourne déjà le monitor
  _cmd=$(tmux display-message -p -t "$SESSION" '#{pane_current_command}' 2>/dev/null || echo "")
  if [[ "$_cmd" == "bash" ]]; then
    echo "ℹ️  Session $SESSION déjà active — attach avec: tmux attach -t $SESSION"
    exit 0
  fi
  tmux kill-session -t "$SESSION" 2>/dev/null || true
fi

# Créer la session avec le dashboard en mode watch
tmux new-session -d -s "$SESSION" -x 120 -y 35
tmux rename-window -t "$SESSION:0" "$WINDOW"

# Lancer le monitor en mode --watch
tmux send-keys -t "$SESSION:0" \
  "cd '$ROOT' && bash scripts/monitor_agents.sh --watch" Enter

echo "✅ Dashboard lancé dans tmux session '$SESSION'"
echo "   Attacher : tmux attach -t $SESSION"
echo "   Détacher  : Ctrl+B puis D"
