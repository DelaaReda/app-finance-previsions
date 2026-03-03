#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  codex_app_queue_worker.sh [options]

Options:
      --state-dir PATH      Dossier etat (defaut: runtime/codex-app-automation)
      --app-name NAME       Nom app macOS (defaut: Codex)
      --chat-mode MODE      same|new (defaut: same)
      --max N               Max messages traites par run (defaut: 3)
      --focus-wait SEC      Delai activation app avant paste
      --post-wait SEC       Delai apres injection
  -h, --help                Affiche cette aide
USAGE
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${CODEX_APP_AUTOMATION_DIR:-$ROOT/runtime/codex-app-automation}"
QUEUE_DIR="$STATE_DIR/queue"
SENT_DIR="$STATE_DIR/sent"
FAILED_DIR="$STATE_DIR/failed"
LOG_FILE="$STATE_DIR/worker.log"
LOCK_DIR="$STATE_DIR/.worker.lock"
APP_NAME="${CODEX_APP_NAME:-Codex}"
CHAT_MODE="${CHAT_MODE:-same}"
MAX_MESSAGES="${MAX_MESSAGES_PER_RUN:-3}"
FOCUS_WAIT="${FOCUS_WAIT_SECONDS:-1.0}"
POST_WAIT="${POST_WAIT_SECONDS:-0.4}"

while (($#)); do
  case "$1" in
    --state-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --state-dir" >&2; exit 2; }
      STATE_DIR="$1"
      QUEUE_DIR="$STATE_DIR/queue"
      SENT_DIR="$STATE_DIR/sent"
      FAILED_DIR="$STATE_DIR/failed"
      LOG_FILE="$STATE_DIR/worker.log"
      LOCK_DIR="$STATE_DIR/.worker.lock"
      ;;
    --app-name)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --app-name" >&2; exit 2; }
      APP_NAME="$1"
      ;;
    --chat-mode)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --chat-mode" >&2; exit 2; }
      CHAT_MODE="$1"
      ;;
    --max)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --max" >&2; exit 2; }
      MAX_MESSAGES="$1"
      ;;
    --focus-wait)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --focus-wait" >&2; exit 2; }
      FOCUS_WAIT="$1"
      ;;
    --post-wait)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --post-wait" >&2; exit 2; }
      POST_WAIT="$1"
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

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only" >&2; exit 2; }
[[ "$MAX_MESSAGES" =~ ^[0-9]+$ ]] || { echo "--max must be integer" >&2; exit 2; }
[[ "$MAX_MESSAGES" -ge 1 ]] || { echo "--max must be >= 1" >&2; exit 2; }

mkdir -p "$QUEUE_DIR" "$SENT_DIR" "$FAILED_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "$(date '+%F %T') worker_locked state_dir=$STATE_DIR" >> "$LOG_FILE"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

processed=0
while (( processed < MAX_MESSAGES )); do
  next_file="$(find "$QUEUE_DIR" -type f -name '*.msg.txt' -print 2>/dev/null | sort | head -n 1)"
  [[ -n "$next_file" ]] || break

  base_name="$(basename "$next_file")"
  ts="$(date '+%F %T')"

  if bash "$ROOT/scripts/codex_app_send_message_mac.sh" \
      --message-file "$next_file" \
      --app-name "$APP_NAME" \
      --chat-mode "$CHAT_MODE" \
      --focus-wait "$FOCUS_WAIT" \
      --post-wait "$POST_WAIT" \
      >> "$LOG_FILE" 2>&1; then
    mv "$next_file" "$SENT_DIR/${base_name%.msg.txt}.sent.txt"
    echo "$ts status=sent file=$base_name app=$APP_NAME mode=$CHAT_MODE" >> "$LOG_FILE"
  else
    mv "$next_file" "$FAILED_DIR/${base_name%.msg.txt}.failed.txt"
    echo "$ts status=failed file=$base_name app=$APP_NAME mode=$CHAT_MODE" >> "$LOG_FILE"
  fi

  processed=$((processed + 1))
done

echo "$(date '+%F %T') processed=$processed queue_dir=$QUEUE_DIR" >> "$LOG_FILE"
echo "processed=$processed"
