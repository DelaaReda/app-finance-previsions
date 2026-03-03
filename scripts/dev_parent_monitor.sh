#!/usr/bin/env bash
# dev_parent_monitor.sh — quality monitor for dev role autonomy/delivery evidence
# Usage:
#   bash scripts/dev_parent_monitor.sh
#   bash scripts/dev_parent_monitor.sh --strict
#   bash scripts/dev_parent_monitor.sh --strict --append-memory
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

STRICT=0
APPEND_MEMORY=0
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --append-memory) APPEND_MEMORY=1 ;;
  esac
done

STATE_DIR_DEFAULT="/home/venom/.openclaw/cron/role-state"
STATE_DIR_ALT="${HOME}/.openclaw/cron/role-state"
if [[ -d "$STATE_DIR_DEFAULT" ]]; then
  STATE_DIR="$STATE_DIR_DEFAULT"
else
  STATE_DIR="$STATE_DIR_ALT"
fi

CONTRACT_FILE="$STATE_DIR/dev.last_contract"
TICK_LOG="$ROOT/logs-codex-runs/fc-ticks/dev.tick.log"
MEMORY_FILE="$ROOT/memory/agents/dev.md"

if [[ ! -f "$CONTRACT_FILE" ]]; then
  echo "DEV_PARENT: BLOCKED"
  echo "reason=missing_contract_file"
  echo "contract_file=$CONTRACT_FILE"
  if [[ "$STRICT" -eq 1 ]]; then
    exit 1
  fi
  echo "strict_verdict=WARN"
  exit 0
fi

evidence_line="$(sed -n 's/^EVIDENCE:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"
task_update="$(printf '%s\n' "$evidence_line" | tr ';' '\n' | sed -n 's/^[[:space:]]*task_update=//p' | head -1)"
status="$(sed -n 's/^STATUS:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"
verdict="$(sed -n 's/^VERDICT:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"
next_action="$(sed -n 's/^NEXT_ACTION_UNIQUE:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"

ev_get() {
  local key="$1"
  printf '%s\n' "$evidence_line" | tr ';' '\n' | sed -n "s/^[[:space:]]*${key}=//p" | head -1 | sed 's/[[:space:]]*$//'
}

missing=()
if [[ "$task_update" == "claim" ]]; then
  for field in root_cause architecture_check vision_alignment reuse_check; do
    val="$(ev_get "$field")"
    if [[ -z "$val" || "${val,,}" == "none" || "${val,,}" == "n/a" || "${val,,}" == "null" || "$val" == "-" ]]; then
      missing+=("$field")
    fi
  done
elif [[ "$task_update" == "complete" || "$task_update" == "handoff" ]]; then
  for field in root_cause fix_applied verify reuse_check architecture_check vision_alignment qa_proof; do
    val="$(ev_get "$field")"
    if [[ -z "$val" || "${val,,}" == "none" || "${val,,}" == "n/a" || "${val,,}" == "null" || "$val" == "-" ]]; then
      missing+=("$field")
    fi
  done
fi

failures_24h="0"
if [[ -f "$TICK_LOG" ]]; then
  failures_24h="$(python3 - "$TICK_LOG" <<'PY'
import re, sys, time
from datetime import datetime
path = sys.argv[1]
now = int(time.time())
cutoff = now - 24*3600
count = 0
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}).*?\[END\].*?rc=(\d+)', line)
        if not m:
            continue
        ts = int(datetime.fromisoformat(m.group(1)).timestamp())
        if ts < cutoff:
            continue
        if int(m.group(2)) != 0:
            count += 1
print(count)
PY
)"
fi

action_markers="0"
contract_markers="0"
if [[ -f "$TICK_LOG" ]]; then
  action_markers="$(tail -n 600 "$TICK_LOG" | grep -c '\[ACTION\]' || true)"
  contract_markers="$(tail -n 600 "$TICK_LOG" | grep -c '\[CONTRACT\]' || true)"
fi

echo "DEV_PARENT: SNAPSHOT"
echo "status=${status:-?} verdict=${verdict:-?} task_update=${task_update:-?}"
echo "failures_last_24h=${failures_24h}"
echo "tick_markers contract=${contract_markers} action=${action_markers}"
echo "next_action=${next_action:-?}"

if [[ "${#missing[@]}" -gt 0 ]]; then
  echo "coaching_gap=missing_evidence_fields:${missing[*]}"
else
  echo "coaching_gap=none"
fi

coach_note="dev_parent $(date -u +%Y-%m-%dT%H:%M:%SZ) status=${status:-?} task_update=${task_update:-?} missing=${missing[*]:-none} failures_24h=${failures_24h} markers=contract:${contract_markers},action:${action_markers}"
if [[ "$APPEND_MEMORY" -eq 1 ]]; then
  mkdir -p "$(dirname "$MEMORY_FILE")"
  if [[ ! -f "$MEMORY_FILE" ]]; then
    printf "# Dev Agent Memory\n\n" > "$MEMORY_FILE"
  fi
  printf -- "- %s\n" "$coach_note" >> "$MEMORY_FILE"
  echo "memory_append=ok file=$MEMORY_FILE"
fi

if [[ "$STRICT" -eq 1 ]]; then
  if [[ "${#missing[@]}" -gt 0 || "$failures_24h" != "0" ]]; then
    echo "strict_verdict=FAIL"
    exit 1
  fi
  if [[ "$action_markers" == "0" || "$contract_markers" == "0" ]]; then
    echo "strict_verdict=FAIL"
    exit 1
  fi
fi

echo "strict_verdict=PASS"
