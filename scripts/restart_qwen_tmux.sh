#!/usr/bin/env bash
# Redémarre les sessions tmux Qwen (planner/dev/tester) en utilisant les scripts start/stop.
# Usage: ./scripts/restart_qwen_tmux.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

./scripts/stop_qwen_tmux.sh
./scripts/start_qwen_tmux.sh
