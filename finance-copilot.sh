#!/usr/bin/env bash
# Wrapper officiel pour démarrer/arrêter Finance Copilot
# Ce script délègue à copilot-app/copilot.sh en conservant les arguments.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="$SCRIPT_DIR/copilot-app/copilot.sh"

if [ ! -x "$TARGET_SCRIPT" ]; then
  echo "Erreur: script cible introuvable ou non exécutable: $TARGET_SCRIPT" >&2
  exit 1
fi

exec "$TARGET_SCRIPT" "$@"
