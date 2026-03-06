#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

usage() {
  cat <<'USAGE'
Usage:
  scripts/preannounce_intent.sh preannounce --role <role> --scope <scope> --files <csv_paths> [--eta-minutes <n>] [--intent-id <id>] [--note <text>] [--allow-overlap]
  scripts/preannounce_intent.sh close --intent-id <id> [--status done|cancelled|blocked] [--note <text>]
  scripts/preannounce_intent.sh list [--json]

Examples:
  scripts/preannounce_intent.sh preannounce --role backend_engineer --scope api_forecast_contract --files docs/product/planning/tasks.md,apps/api/src/platform/main.py --eta-minutes 25
  scripts/preannounce_intent.sh close --intent-id INTENT_BACKEND_ENGINEER_20260226T210000Z --status done
  scripts/preannounce_intent.sh list
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

SUBCMD="$1"
shift

case "$SUBCMD" in
  preannounce|close|list)
    exec python3 scripts/intent_registry.py "$SUBCMD" "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown subcommand: $SUBCMD" >&2
    usage >&2
    exit 2
    ;;
esac
