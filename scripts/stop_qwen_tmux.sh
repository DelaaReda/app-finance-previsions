#!/usr/bin/env bash
# Version PRO : stop propre des sessions + pipe-pane.
set -e

stop_session() {
    local name="$1"
    if tmux has-session -t "$name" 2>/dev/null; then
        tmux pipe-pane -t "${name}.0" 2>/dev/null || true
        tmux kill-session -t "$name"
        echo "🛑 Session stopped: $name"
    fi
}

stop_session "qwen_planner"
stop_session "qwen_dev"
stop_session "qwen_tester"
