#!/usr/bin/env bash
# tick_history.sh — Historique des 20 derniers ticks par rôle
# Usage: bash scripts/tick_history.sh [role] [--n 30]
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

ROLE="${1:-all}"
N="${3:-20}"  # --n <num> via arg 2+3

TICK_LOG="$ROOT/logs-codex-runs/fc-ticks"

iso_to_epoch_local() {
  local iso_ts="$1"
  python3 - "$iso_ts" <<'PY'
import sys
from datetime import datetime
value = (sys.argv[1] or "").strip()
if not value:
    print(0)
    raise SystemExit(0)
try:
    print(int(datetime.fromisoformat(value).timestamp()))
except Exception:
    print(0)
PY
}

reverse_lines() {
  local file="$1"
  if command -v tac >/dev/null 2>&1; then
    tac "$file"
  else
    tail -r "$file"
  fi
}

print_role_history() {
  local role="$1"
  local log="$TICK_LOG/$role.tick.log"
  [[ -f "$log" ]] || { echo "  [$role] log absent"; return; }

  printf '\n  ┌─ %s ─────────────────────────────────────────\n' "$role"

  local prev_ts=""
  local count=0
  while IFS= read -r line; do
    [[ "$line" =~ \[END\]|\[SKIP\]|\[BACKOFF\] ]] || continue
    [[ $count -ge $N ]] && break

    local ts rc agent typ gap=""
    ts=$(printf '%s\n' "$line" | grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
    rc=$(printf '%s\n' "$line" | sed -n 's/.*rc=\([0-9][0-9]*\).*/\1/p' | head -1)
    agent=$(printf '%s\n' "$line" | sed -n 's/.*agent=\([A-Za-z0-9_][A-Za-z0-9_]*\).*/\1/p' | head -1)
    [[ "$line" =~ \[SKIP\]    ]] && typ="SKIP   "
    [[ "$line" =~ \[BACKOFF\] ]] && typ="BACKOFF"
    [[ "$line" =~ \[END\]     ]] && typ="END    "

    # Calcul du gap avec le tick précédent
    if [[ -n "$prev_ts" && -n "$ts" ]]; then
      local ep_cur ep_prev
      ep_cur="$(iso_to_epoch_local "$ts")"
      ep_prev="$(iso_to_epoch_local "$prev_ts")"
      local diff=$(( (ep_cur - ep_prev) / 60 ))
      [[ $diff -gt 0 ]] && gap="${diff}m"
    fi

    local icon; [[ "${rc:-1}" == "0" ]] && icon="✔" || icon="✘"
    printf '  │  %s %s  %-7s  %-6s  %-6s  %s\n' \
      "$icon" "${ts:-          ?         }" "$typ" "${agent:-?}" "rc=${rc:-?}" "${gap:+(+$gap)}"

    prev_ts="$ts"
    (( count++ )) || true
  done < <(reverse_lines "$log" | head -$(( N * 5 )))

  printf '  └──────────────────────────────────────────────\n'
}

if [[ "$ROLE" == "all" ]]; then
  for r in planner dev admin; do print_role_history "$r"; done
else
  print_role_history "$ROLE"
fi
echo ""
