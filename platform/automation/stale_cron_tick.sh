#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

THRESHOLD_SECONDS="${STALE_SWEEP_THRESHOLD_SECONDS:-330}"
SWEEP_SCRIPT="${STALE_SWEEP_TICK_SCRIPT:-scripts/stale_cron_sweep.sh}"

parse_field() {
  local summary="$1"
  local key="$2"
  printf '%s\n' "$summary" | sed -n "s/.*${key}=\\([0-9][0-9]*\\).*/\\1/p" | head -n 1
}

if [[ ! -x "$SWEEP_SCRIPT" ]]; then
  echo "STATUS: BLOCKED"
  echo "DELTA: stale_sweep_script_missing"
  echo "EVIDENCE: script=${SWEEP_SCRIPT}; apply=1"
  echo "RISKS: stale running jobs cannot be auto-healed"
  echo "NEXT: restore stale sweep script and re-run cron tick"
  echo "VERDICT: BLOCKED"
  echo "BLOCKER_ID: STALE_SWEEP_SCRIPT_MISSING"
  echo "NEXT_ACTION_UNIQUE: RESTORE_STALE_SWEEP_SCRIPT_$(date +%Y%m%d%H%M%S)"
  exit 0
fi

set +e
OUT="$(
  bash "$SWEEP_SCRIPT" --apply --threshold "$THRESHOLD_SECONDS" 2>&1
)"
RC=$?
set -e

SUMMARY="$(printf '%s\n' "$OUT" | rg '^SWEEP_SUMMARY ' | tail -n 1 || true)"
if [[ -z "$SUMMARY" ]]; then
  echo "STATUS: BLOCKED"
  echo "DELTA: stale_sweep_no_summary"
  echo "EVIDENCE: rc=${RC}; threshold=${THRESHOLD_SECONDS}; raw=$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-360)"
  echo "RISKS: unknown sweep result; stale cron state may persist"
  echo "NEXT: inspect scripts/stale_cron_sweep.sh output format and rerun"
  echo "VERDICT: BLOCKED"
  echo "BLOCKER_ID: STALE_SWEEP_SUMMARY_MISSING"
  echo "NEXT_ACTION_UNIQUE: FIX_STALE_SWEEP_SUMMARY_$(date +%Y%m%d%H%M%S)"
  exit 0
fi

STALE="$(parse_field "$SUMMARY" "stale")"
RESET_OK="$(parse_field "$SUMMARY" "reset_ok")"
RESET_FAILED="$(parse_field "$SUMMARY" "reset_failed")"
SKIPPED_LIVE="$(parse_field "$SUMMARY" "skipped_live")"
MATCHED="$(parse_field "$SUMMARY" "matched")"

for var_name in STALE RESET_OK RESET_FAILED SKIPPED_LIVE MATCHED; do
  eval "v=\${$var_name:-0}"
  if [[ ! "$v" =~ ^[0-9]+$ ]]; then
    eval "$var_name=0"
  fi
done

STATUS="DONE"
DELTA="stale_sweep_no_action"
VERDICT="PASS"
BLOCKER_ID="NONE"
RISKS="none"
NEXT="continue monitoring"

if [[ "$STALE" -gt 0 && "$RESET_OK" -gt 0 ]]; then
  DELTA="stale_sweep_resets_applied"
  NEXT="verify next cron ticks remain stale_free"
fi

if [[ "$SKIPPED_LIVE" -gt 0 ]]; then
  DELTA="stale_sweep_skipped_live_runners"
  RISKS="some jobs looked stale but had active runner processes"
  NEXT="re-check on next tick after live runs complete"
fi

if [[ "$RESET_FAILED" -gt 0 || "$RC" -ne 0 ]]; then
  STATUS="BLOCKED"
  DELTA="stale_sweep_reset_failed"
  VERDICT="BLOCKED"
  BLOCKER_ID="STALE_SWEEP_RESET_FAILED"
  RISKS="stale running cron state may continue to block orchestration"
  NEXT="manual disable/enable on failed job ids then rerun stale sweep"
fi

echo "STATUS: ${STATUS}"
echo "DELTA: ${DELTA}"
echo "EVIDENCE: threshold_s=${THRESHOLD_SECONDS}; matched=${MATCHED}; stale=${STALE}; reset_ok=${RESET_OK}; reset_failed=${RESET_FAILED}; skipped_live=${SKIPPED_LIVE}; rc=${RC}; summary=${SUMMARY}"
echo "RISKS: ${RISKS}"
echo "NEXT: ${NEXT}"
echo "VERDICT: ${VERDICT}"
echo "BLOCKER_ID: ${BLOCKER_ID}"
echo "NEXT_ACTION_UNIQUE: STALE_SWEEP_TICK_$(date +%Y%m%d%H%M%S)"

