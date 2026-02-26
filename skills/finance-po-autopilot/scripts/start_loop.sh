#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ORCH="$WORKDIR/scripts/qwen_orchestrator.py"
AGENT_BIN_DEFAULT="/home/venom/.npm-global/bin/qwen"

FEATURE=""
ROUNDS=3
CYCLES=3
INTERVAL_MIN=15
AGENT_BIN="${FC_AGENT_BIN:-$AGENT_BIN_DEFAULT}"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="$2"; shift 2 ;;
    --rounds) ROUNDS="$2"; shift 2 ;;
    --cycles) CYCLES="$2"; shift 2 ;;
    --interval-min) INTERVAL_MIN="$2"; shift 2 ;;
    --agent-bin) AGENT_BIN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$FEATURE" ]]; then
  echo "Missing --feature" >&2
  exit 2
fi

if [[ ! -f "$ORCH" ]]; then
  echo "Orchestrator not found: $ORCH" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$WORKDIR/finance-app/openclaw-autopilot/$STAMP"
mkdir -p "$LOG_DIR"

for ((i=1; i<=CYCLES; i++)); do
  echo "[cycle $i/$CYCLES] feature=$FEATURE" | tee -a "$LOG_DIR/loop.log"
  CMD=(python3 "$ORCH" --feature "$FEATURE" --rounds "$ROUNDS" --with-manager --with-architect --agent-bin "$AGENT_BIN")

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ${CMD[*]}" | tee -a "$LOG_DIR/loop.log"
  else
    (
      cd "$WORKDIR"
      FC_AGENT_BIN="$AGENT_BIN" "${CMD[@]}"
    ) >> "$LOG_DIR/cycle-$i.log" 2>&1 || true
  fi

  if [[ "$i" -lt "$CYCLES" ]]; then
    echo "[sleep] ${INTERVAL_MIN}m" | tee -a "$LOG_DIR/loop.log"
    [[ "$DRY_RUN" -eq 1 ]] || sleep "$((INTERVAL_MIN * 60))"
  fi
done

echo "Autopilot logs: $LOG_DIR"
