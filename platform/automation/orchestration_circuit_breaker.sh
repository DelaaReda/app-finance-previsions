#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

WINDOW_MINUTES="${CB_WINDOW_MINUTES:-15}"
ERROR_THRESHOLD="${CB_ERROR_THRESHOLD:-3}"
APPLY=0
STOP_SESSIONS=1
TARGET_MODE="${CB_TARGET_MODE:-paused}"

usage() {
  cat <<'EOF'
Usage: orchestration_circuit_breaker.sh [options]

Options:
  --window-minutes <n>    Logical lookback window label (default: 15)
  --error-threshold <n>   Trigger threshold on jobs with lastStatus=error (default: 3)
  --target-mode <mode>    Mode applied when triggered (default: paused)
  --apply                 Apply mode switch when triggered
  --no-stop-sessions      Keep tmux sessions alive on trigger
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window-minutes) WINDOW_MINUTES="${2:-}"; shift 2 ;;
    --error-threshold) ERROR_THRESHOLD="${2:-}"; shift 2 ;;
    --target-mode) TARGET_MODE="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --no-stop-sessions) STOP_SESSIONS=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! [[ "$WINDOW_MINUTES" =~ ^[0-9]+$ ]] || [[ "$WINDOW_MINUTES" -lt 1 ]]; then
  WINDOW_MINUTES=15
fi
if ! [[ "$ERROR_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$ERROR_THRESHOLD" -lt 1 ]]; then
  ERROR_THRESHOLD=3
fi

if ! command -v openclaw >/dev/null 2>&1; then
  echo "CIRCUIT_BREAKER status=BLOCKED reason=openclaw_missing"
  exit 3
fi

cron_json="$(openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
total_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[]?] | length' 2>/dev/null || echo 0)"
error_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.state.lastStatus // "")=="error")] | length' 2>/dev/null || echo 0)"
running_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select(.state.runningAtMs!=null)] | length' 2>/dev/null || echo 0)"
blocked_like_jobs="$(printf '%s' "$cron_json" | jq '[.jobs[]? | select((.state.lastError // "") | test("blocked|contract|lock"; "i"))] | length' 2>/dev/null || echo 0)"

triggered=0
if [[ "$error_jobs" -ge "$ERROR_THRESHOLD" ]]; then
  triggered=1
fi

action="none"
action_result="none"
if [[ "$triggered" -eq 1 && "$APPLY" -eq 1 ]]; then
  if [[ "$STOP_SESSIONS" -eq 1 ]]; then
    if bash scripts/set_orchestration_mode.sh --mode "$TARGET_MODE" --stop-sessions >/tmp/circuit-breaker-mode.out 2>&1; then
      action="set_mode_${TARGET_MODE}_stop_sessions"
      action_result="done"
    else
      action="set_mode_${TARGET_MODE}_stop_sessions"
      action_result="failed"
    fi
  else
    if bash scripts/set_orchestration_mode.sh --mode "$TARGET_MODE" >/tmp/circuit-breaker-mode.out 2>&1; then
      action="set_mode_${TARGET_MODE}"
      action_result="done"
    else
      action="set_mode_${TARGET_MODE}"
      action_result="failed"
    fi
  fi
fi

status="PASS"
if [[ "$triggered" -eq 1 ]]; then
  status="TRIGGERED"
fi
if [[ "$triggered" -eq 1 && "$APPLY" -eq 1 && "$action_result" != "done" ]]; then
  status="BLOCKED"
fi

echo "CIRCUIT_BREAKER status=${status} window_min=${WINDOW_MINUTES} total_jobs=${total_jobs} error_jobs=${error_jobs} blocked_like_jobs=${blocked_like_jobs} running_jobs=${running_jobs} threshold=${ERROR_THRESHOLD} apply=${APPLY} action=${action} action_result=${action_result}"

if [[ "$status" == "BLOCKED" ]]; then
  exit 2
fi
if [[ "$status" == "TRIGGERED" ]]; then
  exit 1
fi
exit 0

