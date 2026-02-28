#!/usr/bin/env bash
# Wrapper officiel pour démarrer/arrêter Finance Copilot.
# Délègue au launcher central du backend dans `apps/api/runtime`.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="$SCRIPT_DIR/apps/api/runtime/copilot.sh"

if [ ! -x "$TARGET_SCRIPT" ]; then
  echo "Erreur: script cible introuvable ou non exécutable: $TARGET_SCRIPT" >&2
  exit 1
fi

exec "$TARGET_SCRIPT" "$@"
