#!/usr/bin/env bash
# Version PRO : restart = stop + start
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")"; pwd)"

echo "♻️  Restarting all Qwen tmux sessions..."
"$SCRIPT_DIR/stop_qwen_tmux.sh"
"$SCRIPT_DIR/start_qwen_tmux.sh"
echo "✓ Restart done."
