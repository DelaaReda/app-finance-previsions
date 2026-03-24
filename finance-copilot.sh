#!/usr/bin/env bash
# Wrapper officiel pour démarrer/arrêter Finance Copilot.
# Délègue au launcher central du backend dans `apps/api/runtime`.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_HOST_GUARD="$SCRIPT_DIR/platform/automation/lib/runtime_host_guard.sh"
TARGET_SCRIPT="$SCRIPT_DIR/apps/api/runtime/copilot.sh"

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
  API_BASE_URL="${FC_API_BASE_URL:-http://127.0.0.1:8050}"
  MONITOR_BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
  FRONTEND_BASE_URL="${FC_FRONTEND_BASE_URL:-http://127.0.0.1:5173}"

  "$TARGET_SCRIPT" start
  curl -fsS --max-time 5 "${FRONTEND_BASE_URL%/}/" >/dev/null
  curl -fsS --max-time 5 "${MONITOR_BASE_URL%/}/api/status?lite=1" >/dev/null
  exec bash "$SCRIPT_DIR/scripts/critical_endpoints_smoke.sh" --base-url "$API_BASE_URL" "$@"
fi

exec "$TARGET_SCRIPT" "$@"
