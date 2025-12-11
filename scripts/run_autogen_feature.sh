#!/usr/bin/env bash
# Lance un cycle complet Autogen GroupChat (Planner/Dev/Tester + QA) avec Qwen Code.
# Usage : 
#   ./scripts/run_autogen_feature.sh "Ta feature à traiter"
#   FC_FEATURE="Refactor cache" ./scripts/run_autogen_feature.sh

set -euo pipefail

REPO="/Users/venom/Documents/analyse-financiere"
BACKEND="$REPO/copilot-app/backend"
VENV="$BACKEND/.venv/bin/activate"

FEATURE="${1:-${FC_FEATURE:-}}"

cd "$REPO"

echo "🚀 Démarrage des sessions tmux Qwen..."
./scripts/start_qwen_tmux.sh

echo "📦 Activation venv backend..."
# shellcheck disable=SC1090
source "$VENV"

echo "🧠 Lancement Autogen GroupChat (Planner/Dev/Tester + QA)..."
export PYTHONPATH="$REPO"
if [ -n "$FEATURE" ]; then
  FC_FEATURE="$FEATURE" python scripts/autogen_groupchat_qwen.py
else
  python scripts/autogen_groupchat_qwen.py
fi

echo "✅ Terminé. (Les sessions tmux restent ouvertes : stop avec ./scripts/stop_qwen_tmux.sh)"
