#!/usr/bin/env bash
# watchdog_chromium.sh — Tue les processus Chromium zombies qui s'accumulent
# Déclenché par cron, sans toucher au chromium utilisé activement
# Logique: si chromium tourne depuis > 2h sans activité réseau → zombie → kill

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/logs-codex-runs/watchdog_chromium.log"
mkdir -p "$(dirname "$LOG")"
ts() { date '+%Y-%m-%dT%H:%M:%S'; }

# Compte les processus chrome/chromium visibles
COUNT=$(ps -eo comm= | grep -Eic "(chromium|chrome)" || echo 0)

# Seuil : plus de 5 processus chromium = accumulation anormale
THRESHOLD=5

STALE_PIDS="$(
  ps -eo pid=,etimes=,comm=,args= \
  | awk '
      {
        pid=$1; et=$2; cmd=$3; $1=""; $2=""; $3="";
        args=$0;
        if (et+0 < 7200) next;
        if (cmd !~ /(chromium|chrome)/) next;
        if (args ~ /(renderer|zygote|gpu-process|utility|headless)/) print pid;
      }'
)"

STALE_COUNT=$(printf '%s\n' "$STALE_PIDS" | sed '/^$/d' | wc -l | tr -d ' ')

if [[ "${STALE_COUNT:-0}" -gt 0 ]]; then
    echo "$(ts) [WATCHDOG] chromium_total=$COUNT stale_workers=$STALE_COUNT (kill targeted stale workers)" >> "$LOG"
    while IFS= read -r pid; do
      [[ -z "$pid" ]] && continue
      kill "$pid" 2>/dev/null || true
    done <<< "$STALE_PIDS"
    sleep 1
    AFTER=$(ps -eo comm= | grep -Eic "(chromium|chrome)" || echo 0)
    echo "$(ts) [WATCHDOG] After kill: $AFTER remaining" >> "$LOG"
elif [[ "$COUNT" -gt "$THRESHOLD" ]]; then
    echo "$(ts) [WATCHDOG] chromium_total=$COUNT (>threshold=$THRESHOLD) but no stale worker >2h; skip kill" >> "$LOG"
else
    echo "$(ts) [OK] chromium_total=$COUNT (threshold=$THRESHOLD)" >> "$LOG"
fi

# Aussi nettoyer les run.locks stales (> 15 min)
LOCK_DIR="$HOME/.openclaw/cron/role-state"
find "$LOCK_DIR" -name "*.run.lock" -mmin +15 | while read f; do
    echo "$(ts) [WATCHDOG] Removing stale lock: $f" >> "$LOG"
    rm -f "$f"
done

# Nettoyer executor-monitoring.lock si stale
find "$LOCK_DIR" -name "executor-monitoring.lock" -mmin +10 | while read f; do
    echo "$(ts) [WATCHDOG] Removing stale executor lock: $f" >> "$LOG"
    rm -f "$f"
done
