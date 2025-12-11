#!/usr/bin/env bash
# Redémarre les sessions tmux Qwen (stop puis start).
# Usage: ./scripts/restart_qwen_tmux.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "${ROOT_DIR}/scripts/stop_qwen_tmux.sh" ]] || [[ ! -x "${ROOT_DIR}/scripts/start_qwen_tmux.sh" ]]; then
  echo "Scripts start/stop introuvables dans ${ROOT_DIR}/scripts" >&2
  exit 1
fi

"${ROOT_DIR}/scripts/stop_qwen_tmux.sh"
"${ROOT_DIR}/scripts/start_qwen_tmux.sh"
