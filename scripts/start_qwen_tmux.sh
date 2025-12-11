#!/usr/bin/env bash
# Version PRO : démarre les sessions tmux Qwen avec logs en temps réel.
# Sessions : qwen_planner, qwen_dev, qwen_tester
# Logs : logs/qwen_planner.log, logs/qwen_dev.log, logs/qwen_tester.log

set -e

BASE_DIR="$(cd "$(dirname "$0")/.."; pwd)"
LOG_DIR="$BASE_DIR/logs"
PATH_OVERRIDE="/opt/homebrew/bin:/usr/local/bin:$PATH"
QWEN_BIN="$(command -v qwen || true)"

mkdir -p "$LOG_DIR"

# Rotation simple : on vide les logs à chaque start
echo "" > "$LOG_DIR/qwen_planner.log"
echo "" > "$LOG_DIR/qwen_dev.log"
echo "" > "$LOG_DIR/qwen_tester.log"

echo "🚀 Starting Qwen tmux sessions with live logging..."

start_session() {
    local name="$1"
    local log_file="$LOG_DIR/${name}.log"

    # Créer la session détachée et lancer qwen directement
    tmux new-session -d -s "$name" "bash -lc 'cd \"${BASE_DIR}\" && export PATH=\"${PATH_OVERRIDE}\" && export QWEN_CODE_AUTO_CONFIRM=1 && ${QWEN_BIN:-qwen} || exec bash'"

    # Pipe temps réel vers le log
    tmux pipe-pane -o -t "${name}.0" "cat >> \"$log_file\""

    echo "✓ Session $name started → logs streaming to: $log_file"
}

# Si les sessions existent déjà, on les tue pour garantir un start propre
tmux has-session -t qwen_planner 2>/dev/null && tmux kill-session -t qwen_planner || true
tmux has-session -t qwen_dev 2>/dev/null && tmux kill-session -t qwen_dev || true
tmux has-session -t qwen_tester 2>/dev/null && tmux kill-session -t qwen_tester || true

start_session "qwen_planner"
start_session "qwen_dev"
start_session "qwen_tester"

echo ""
echo "ℹ️  Attach with: tmux attach -t qwen_planner"
echo "ℹ️  Logs live: tail -f logs/qwen_planner.log"
