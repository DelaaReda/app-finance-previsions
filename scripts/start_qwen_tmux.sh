#!/usr/bin/env bash
# Launch three tmux sessions running `qwen` in the repo directory.
# Sessions: qwen_planner, qwen_dev, qwen_tester
# Usage: ./scripts/start_qwen_tmux.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_ROOT="${PROJECT_DIR}/logs"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="${LOG_ROOT}/${RUN_ID}"
PATH_OVERRIDE="/opt/homebrew/bin:/usr/local/bin:$PATH"
QWEN_BIN="$(command -v qwen || true)"

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Project directory not found: ${PROJECT_DIR}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"

start_session() {
  local name=$1
  tmux has-session -t "${name}" 2>/dev/null && return 0

  tmux new-session -d -s "${name}" "bash -lc 'cd \"${PROJECT_DIR}\" && export PATH=\"${PATH_OVERRIDE}\" && export QWEN_CODE_AUTO_CONFIRM=1 && ${QWEN_BIN:-qwen} || exec bash'"

  # Pipe pane output to log (append)
  tmux pipe-pane -o -t "${name}" "cat >> \"${LOG_DIR}/${name}.log\""
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
echo "Logs: ${LOG_DIR}/qwen_*.log"
