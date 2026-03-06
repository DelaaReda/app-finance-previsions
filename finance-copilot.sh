#!/usr/bin/env bash
# Wrapper officiel pour démarrer/arrêter Finance Copilot.
# Délègue au launcher central du backend dans `apps/api/runtime`.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_HOST_GUARD="$SCRIPT_DIR/platform/automation/lib/runtime_host_guard.sh"
TARGET_SCRIPT="$SCRIPT_DIR/apps/api/runtime/copilot.sh"
GATE_SCRIPT="$SCRIPT_DIR/scripts/runtime_gate.sh"

if [[ ! -f "$RUNTIME_HOST_GUARD" ]]; then
  echo "Erreur: runtime host guard introuvable: $RUNTIME_HOST_GUARD" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$RUNTIME_HOST_GUARD"
fc_runtime_assert_vm_or_exit "finance-copilot"

if [ ! -x "$TARGET_SCRIPT" ]; then
  echo "Erreur: script cible introuvable ou non exécutable: $TARGET_SCRIPT" >&2
  exit 1
fi

if [[ "${1:-}" == "gate" ]]; then
  shift || true
  if [[ ! -f "$GATE_SCRIPT" ]]; then
    echo "Erreur: script gate introuvable: $GATE_SCRIPT" >&2
    exit 1
  fi
  exec bash "$GATE_SCRIPT" "$@"
fi

exec "$TARGET_SCRIPT" "$@"
