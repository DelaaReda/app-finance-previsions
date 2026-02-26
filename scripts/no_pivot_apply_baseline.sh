#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MODE="apply"
STOP_SESSIONS=1
SKILL_HARDEN=1

usage() {
  cat <<'EOF'
Usage: no_pivot_apply_baseline.sh [options]

Apply a stable OpenClaw baseline for codex-only orchestration:
- pause all cron jobs
- optional tmux session stop
- bounded subagent concurrency
- bounded cron retention/log size
- disable legacy/high-autonomy skills likely to cause drift

Options:
  --dry-run            Print actions only
  --apply              Apply changes (default)
  --no-stop-sessions   Keep tmux sessions alive while pausing cron jobs
  --no-skill-harden    Keep current skill enablement state
  -h, --help           Show help
EOF
}

run_cmd() {
  if [[ "$MODE" == "dry-run" ]]; then
    printf 'DRY_RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    --no-stop-sessions)
      STOP_SESSIONS=0
      shift
      ;;
    --no-skill-harden)
      SKILL_HARDEN=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw not found in PATH" >&2
  exit 2
fi

if [[ "$MODE" == "apply" && -f "$HOME/.openclaw/openclaw.json" ]]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  backup="$HOME/.openclaw/openclaw.json.backup-no-pivot-${ts}"
  cp "$HOME/.openclaw/openclaw.json" "$backup"
  echo "CONFIG_BACKUP=$backup"
fi

pause_args=(bash "$ROOT/scripts/set_orchestration_mode.sh" --mode paused)
if [[ "$STOP_SESSIONS" -eq 1 ]]; then
  pause_args+=(--stop-sessions)
fi
run_cmd "${pause_args[@]}"

# Runtime guardrails
run_cmd openclaw config set agents.defaults.maxConcurrent 2 --strict-json
run_cmd openclaw config set agents.defaults.subagents.maxConcurrent 3 --strict-json
run_cmd openclaw config set agents.defaults.heartbeat.every '"30m"' --strict-json

# Log/session retention guardrails for cron runs
run_cmd openclaw config set cron.sessionRetention '"8h"' --strict-json
run_cmd openclaw config set cron.runLog.maxBytes 500000 --strict-json
run_cmd openclaw config set cron.runLog.keepLines 500 --strict-json

if [[ "$SKILL_HARDEN" -eq 1 ]]; then
  # Keep codex-only posture and avoid accidental legacy/autonomous orchestration drift.
  run_cmd openclaw config set skills.entries.finance-po-autopilot.enabled false --strict-json
  run_cmd openclaw config set skills.entries.finance-po-orchestrator.enabled false --strict-json
  run_cmd openclaw config set skills.entries.task-orchestrator.enabled false --strict-json
  run_cmd openclaw config set skills.entries.autonomous-skill-orchestrator.enabled false --strict-json
  run_cmd openclaw config set skills.entries.joko-orchestrator.enabled false --strict-json
  run_cmd openclaw config set skills.entries.cc-godmode.enabled false --strict-json
fi

if [[ "$MODE" == "apply" ]]; then
  echo "NO_PIVOT_BASELINE_APPLIED"
  openclaw config get agents.defaults.maxConcurrent
  openclaw config get agents.defaults.subagents.maxConcurrent
  openclaw config get agents.defaults.heartbeat.every
  openclaw config get cron.sessionRetention
  openclaw config get cron.runLog.maxBytes
  openclaw config get cron.runLog.keepLines
  openclaw config get skills.entries.finance-po-autopilot.enabled
  openclaw config get skills.entries.finance-po-orchestrator.enabled
  openclaw config get skills.entries.task-orchestrator.enabled
  openclaw config get skills.entries.autonomous-skill-orchestrator.enabled
  openclaw config get skills.entries.joko-orchestrator.enabled
  openclaw config get skills.entries.cc-godmode.enabled
  openclaw cron list || true
else
  echo "NO_PIVOT_BASELINE_DRY_RUN_DONE"
fi
