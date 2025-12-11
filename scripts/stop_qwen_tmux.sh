#!/usr/bin/env bash
# Stop tmux sessions used for Qwen agents.
# Usage: ./scripts/stop_qwen_tmux.sh

set -euo pipefail

sessions=(qwen_planner qwen_dev qwen_tester)

for s in "${sessions[@]}"; do
  if tmux has-session -t "$s" 2>/dev/null; then
    tmux kill-session -t "$s"
    echo "Session tmux arrêtée : $s"
  fi
done

# Si plus aucune session tmux ne tourne, tmux ls retournera une erreur; on ignore
tmux ls 2>/dev/null || true
