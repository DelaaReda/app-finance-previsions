#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${CODEX_APP_AUTOMATION_DIR:-$ROOT/runtime/codex-app-automation}"
QUEUE_DIR="$STATE_DIR/queue"
LAST_FILE="$STATE_DIR/supervision.last_epoch"
PROMPT_FILE="${PROMPT_FILE:-$ROOT/docs/ops/prompts/CODEX_SUPERVISION_SAME_PROMPT.txt}"
MIN_INTERVAL_SECONDS="${MIN_INTERVAL_SECONDS:-14400}"

usage() {
  cat <<'USAGE'
Usage:
  codex_app_enqueue_supervision_prompt.sh [options]

Options:
      --state-dir PATH      Etat runtime (defaut: runtime/codex-app-automation)
      --prompt-file PATH    Prompt a envoyer
      --min-interval SEC    Cooldown entre 2 envois (defaut: 14400 = 4h)
      --force               Ignore cooldown
  -h, --help               Aide
USAGE
}

FORCE=0
while (($#)); do
  case "$1" in
    --state-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --state-dir" >&2; exit 2; }
      STATE_DIR="$1"
      QUEUE_DIR="$STATE_DIR/queue"
      LAST_FILE="$STATE_DIR/supervision.last_epoch"
      ;;
    --prompt-file)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --prompt-file" >&2; exit 2; }
      PROMPT_FILE="$1"
      ;;
    --min-interval)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --min-interval" >&2; exit 2; }
      MIN_INTERVAL_SECONDS="$1"
      ;;
    --force)
      FORCE=1
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
  shift
done

[[ "$MIN_INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || { echo "min interval must be integer" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 2; }

mkdir -p "$QUEUE_DIR"

pending_count="$(find "$QUEUE_DIR" -type f -name '*supervision*.msg.txt' 2>/dev/null | wc -l | tr -d ' ')"
[[ -n "$pending_count" ]] || pending_count=0
if [[ "$pending_count" -gt 0 ]]; then
  echo "queued=0"
  echo "reason=pending_supervision_message"
  echo "pending=$pending_count"
  exit 0
fi

now_epoch="$(date +%s)"
last_epoch=0
if [[ -f "$LAST_FILE" ]]; then
  last_epoch="$(tr -d '[:space:]' < "$LAST_FILE" 2>/dev/null || echo 0)"
  [[ "$last_epoch" =~ ^[0-9]+$ ]] || last_epoch=0
fi

if [[ "$FORCE" -ne 1 && "$last_epoch" -gt 0 ]]; then
  delta=$(( now_epoch - last_epoch ))
  if [[ "$delta" -lt "$MIN_INTERVAL_SECONDS" ]]; then
    echo "queued=0"
    echo "reason=cooldown_active"
    echo "remaining=$((MIN_INTERVAL_SECONDS - delta))"
    exit 0
  fi
fi

enqueue_out="$(bash "$ROOT/scripts/codex_app_enqueue_message.sh" --state-dir "$STATE_DIR" --message-file "$PROMPT_FILE")"
msg_file="$(printf '%s\n' "$enqueue_out" | awk -F= '/^file=/{print $2; exit}')"

if [[ -n "$msg_file" && -f "$msg_file" ]]; then
  supervision_file="${msg_file%.msg.txt}.supervision.msg.txt"
  mv "$msg_file" "$supervision_file"
  msg_file="$supervision_file"
fi

printf '%s\n' "$now_epoch" > "$LAST_FILE"

echo "queued=1"
echo "file=${msg_file:-unknown}"
echo "prompt_file=$PROMPT_FILE"
echo "cooldown=$MIN_INTERVAL_SECONDS"
