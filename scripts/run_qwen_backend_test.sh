#!/usr/bin/env bash
# Exécute le quick_test de qwen_tmux_backend.py sans manip manuelle du venv.
# Usage: ./scripts/run_qwen_backend_test.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/copilot-app/backend"
VENV="${BACKEND_DIR}/.venv/bin/python"

if [[ ! -x "${VENV}" ]]; then
  echo "Venv Python introuvable: ${VENV}"
  exit 1
fi

cd "${ROOT_DIR}"
"${VENV}" scripts/qwen_tmux_backend.py
