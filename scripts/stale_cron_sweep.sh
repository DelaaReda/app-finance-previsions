#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

THRESHOLD_SECONDS="${STALE_SWEEP_THRESHOLD_SECONDS:-330}"
ROLE_REGEX="${STALE_SWEEP_ROLE_REGEX:--tmux-loop$}"
OPENCLAW_BIN="${STALE_SWEEP_OPENCLAW_BIN:-}"
APPLY=0

usage() {
  cat <<'EOF'
Usage: stale_cron_sweep.sh [--apply] [--dry-run] [--threshold <seconds>] [--regex <jq-regex>] [--openclaw-bin <path>]

Detect cron jobs stuck in running state (runningAtMs stale, no live role-runner process),
and optionally reset them with disable/enable.

Output:
  SWEEP_ITEM ...
  SWEEP_SUMMARY matched=<n> stale=<n> reset_ok=<n> reset_failed=<n> skipped_live=<n> threshold_s=<n> apply=<0|1>
EOF
}

resolve_openclaw_bin() {
  local candidate=""
  if [[ -n "$OPENCLAW_BIN" && -x "$OPENCLAW_BIN" ]]; then
    printf '%s\n' "$OPENCLAW_BIN"
    return 0
  fi
  for candidate in \
    "/home/venom/.npm-global/bin/openclaw" \
    "${HOME}/.npm-global/bin/openclaw" \
    "$(command -v openclaw 2>/dev/null || true)" \
    "/usr/local/bin/openclaw" \
    "/usr/bin/openclaw" \
    "/bin/openclaw"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --dry-run)
      APPLY=0
      shift
      ;;
    --threshold)
      THRESHOLD_SECONDS="${2:-}"
      shift 2
      ;;
    --regex)
      ROLE_REGEX="${2:-}"
      shift 2
      ;;
    --openclaw-bin)
      OPENCLAW_BIN="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$THRESHOLD_SECONDS" =~ ^[0-9]+$ ]] || [[ "$THRESHOLD_SECONDS" -lt 1 ]]; then
  THRESHOLD_SECONDS=330
fi

if ! OPENCLAW_BIN="$(resolve_openclaw_bin)"; then
  echo "SWEEP_SUMMARY matched=0 stale=0 reset_ok=0 reset_failed=0 skipped_live=0 threshold_s=${THRESHOLD_SECONDS} apply=${APPLY} error=openclaw_missing"
  exit 5
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "SWEEP_SUMMARY matched=0 stale=0 reset_ok=0 reset_failed=0 skipped_live=0 threshold_s=${THRESHOLD_SECONDS} apply=${APPLY} error=jq_missing"
  exit 5
fi

cron_json="$("$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[] }')"
now_epoch="$(date -u +%s)"

matched=0
stale=0
reset_ok=0
reset_failed=0
skipped_live=0

while IFS=$'\t' read -r id name role running_ms; do
  matched=$((matched + 1))
  if [[ -z "$running_ms" || "$running_ms" == "null" ]]; then
    continue
  fi
  if ! [[ "$running_ms" =~ ^[0-9]+$ ]]; then
    continue
  fi

  age=$((now_epoch - (running_ms / 1000)))
  if [[ "$age" -lt "$THRESHOLD_SECONDS" ]]; then
    continue
  fi

  if [[ -z "$role" || "$role" == "null" ]]; then
    role="$(printf '%s' "$name" | sed -E 's/-tmux-loop$//' | tr '-' '_')"
  fi
  role="${role:-unknown}"

  if pgrep -af "cron_tmux_role_runner.sh ${role}" >/dev/null 2>&1; then
    skipped_live=$((skipped_live + 1))
    echo "SWEEP_ITEM id=${id} name=${name} role=${role} age_s=${age} action=skip_live_runner"
    continue
  fi

  stale=$((stale + 1))
  if [[ "$APPLY" -eq 1 ]]; then
    if "$OPENCLAW_BIN" cron disable "$id" >/dev/null 2>&1 && "$OPENCLAW_BIN" cron enable "$id" >/dev/null 2>&1; then
      reset_ok=$((reset_ok + 1))
      echo "SWEEP_ITEM id=${id} name=${name} role=${role} age_s=${age} action=reset_ok"
    else
      reset_failed=$((reset_failed + 1))
      echo "SWEEP_ITEM id=${id} name=${name} role=${role} age_s=${age} action=reset_failed"
    fi
  else
    echo "SWEEP_ITEM id=${id} name=${name} role=${role} age_s=${age} action=stale_detected"
  fi
done < <(
  printf '%s' "$cron_json" \
    | jq -r --arg re "$ROLE_REGEX" '.jobs[]? | select((.name // "") | test($re)) | [.id, .name, (.agentId // "null"), (.state.runningAtMs // "null")] | @tsv'
)

echo "SWEEP_SUMMARY matched=${matched} stale=${stale} reset_ok=${reset_ok} reset_failed=${reset_failed} skipped_live=${skipped_live} threshold_s=${THRESHOLD_SECONDS} apply=${APPLY}"

if [[ "$APPLY" -eq 1 && "$reset_failed" -gt 0 ]]; then
  exit 9
fi
exit 0
