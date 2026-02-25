#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/venom/analyse-financiere"
FORCE_CONFIRM=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      WORKDIR="$2"; shift 2 ;;
    --force-confirm)
      FORCE_CONFIRM=1; shift ;;
    --)
      shift; break ;;
    *)
      break ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "Usage: scripts/exec_safe.sh [--workdir <dir>] [--force-confirm] -- '<command>'" >&2
  exit 2
fi

CMD="$*"
GATE_JSON="$(python3 /home/venom/analyse-financiere/scripts/command_safety_gate.py --cmd "$CMD" --workdir "$WORKDIR")"
DECISION="$(printf '%s' "$GATE_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin)["decision"])')"

echo "$GATE_JSON"

if [[ "$DECISION" == "BLOCK" ]]; then
  echo "[exec_safe] BLOCKED command" >&2
  exit 40
fi

if [[ "$DECISION" == "CONFIRM" && "$FORCE_CONFIRM" -ne 1 ]]; then
  echo "[exec_safe] CONFIRM risk detected; auto-proceed enabled by policy (no user wait)." >&2
fi

cd "$WORKDIR"
exec bash -lc "$CMD"
