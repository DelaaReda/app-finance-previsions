#!/usr/bin/env bash
# Launch three tmux sessions running `qwen` in the repo directory.
# Sessions: qwen_planner, qwen_dev, qwen_tester
# Usage: ./scripts/start_qwen_tmux.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Project directory not found: ${PROJECT_DIR}" >&2
  exit 1
fi

start_session() {
  local name=$1
  tmux has-session -t "${name}" 2>/dev/null || \
    tmux new-session -d -s "${name}" "cd '${PROJECT_DIR}' && qwen"
}

start_session qwen_planner
start_session qwen_dev
start_session qwen_tester

echo "Sessions tmux lancées dans ${PROJECT_DIR}:"
echo "  - qwen_planner"
echo "  - qwen_dev"
echo "  - qwen_tester"
echo
echo "Vérifie avec: tmux ls"
echo "Attache: tmux attach -t qwen_planner"
