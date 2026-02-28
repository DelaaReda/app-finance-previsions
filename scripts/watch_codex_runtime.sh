#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: watch_codex_runtime.sh [--interval <seconds>] [--once]

Poller de surveillance légère pour les crons Codex/OpenClaw.
Affiche un état compact cron, puis un check de sessions tmux.

Options:
  --interval <seconds>  Délai entre deux itérations (par défaut: 120)
  --once                Exécuter un seul cycle et sortir
  -h, --help            Afficher l'aide
USAGE
}

INTERVAL=120
RUN_ONCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval)
      INTERVAL="${2:-}"
      shift 2
      ;;
    --once)
      RUN_ONCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: option inconnue: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]] || [[ "$INTERVAL" -lt 10 ]]; then
  echo "ERROR: --interval doit être un entier >= 10" >&2
  exit 2
fi

while true; do
  now="$(date -Iseconds)"
  echo "===== ${now} ====="
  bash scripts/cron_run_manager.sh status --stale-threshold 180 | sed -n '1,25p'
  bash scripts/tmux_codex_live_monitor.sh --mode status --engine capture --include-admin | sed -n '1,40p'

  if [[ "$RUN_ONCE" -eq 1 ]]; then
    break
  fi

  sleep "$INTERVAL"
done
