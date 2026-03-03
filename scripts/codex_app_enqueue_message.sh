#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  codex_app_enqueue_message.sh --message "text"
  codex_app_enqueue_message.sh --message-file /path/msg.txt
  codex_app_enqueue_message.sh --stdin

Options:
  -m, --message TEXT        Message a placer en queue
      --message-file PATH   Lire le message depuis un fichier
      --stdin               Lire le message depuis stdin
      --state-dir PATH      Dossier etat queue (defaut: runtime/codex-app-automation)
  -h, --help                Affiche cette aide
USAGE
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${CODEX_APP_AUTOMATION_DIR:-$ROOT/runtime/codex-app-automation}"
QUEUE_DIR="$STATE_DIR/queue"

MESSAGE=""
MESSAGE_FILE=""
READ_STDIN=0

while (($#)); do
  case "$1" in
    -m|--message)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --message" >&2; exit 2; }
      MESSAGE="$1"
      ;;
    --message-file)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --message-file" >&2; exit 2; }
      MESSAGE_FILE="$1"
      ;;
    --stdin)
      READ_STDIN=1
      ;;
    --state-dir)
      shift
      [[ $# -gt 0 ]] || { echo "Missing value for --state-dir" >&2; exit 2; }
      STATE_DIR="$1"
      QUEUE_DIR="$STATE_DIR/queue"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$MESSAGE" ]]; then
        MESSAGE+=" $1"
      else
        MESSAGE="$1"
      fi
      ;;
  esac
  shift
done

if [[ -n "$MESSAGE_FILE" ]]; then
  [[ -f "$MESSAGE_FILE" ]] || { echo "message file not found: $MESSAGE_FILE" >&2; exit 2; }
  MESSAGE="$(cat "$MESSAGE_FILE")"
fi

if [[ "$READ_STDIN" -eq 1 ]]; then
  STDIN_PAYLOAD="$(cat)"
  if [[ -n "$MESSAGE" ]]; then
    MESSAGE+=$'\n'
  fi
  MESSAGE+="$STDIN_PAYLOAD"
fi

[[ -n "$MESSAGE" ]] || { echo "message is empty" >&2; exit 2; }

mkdir -p "$QUEUE_DIR"

stamp="$(date +%Y%m%d-%H%M%S)"
nonce="$(printf '%06d' "$RANDOM")"
msg_file="$QUEUE_DIR/${stamp}-${nonce}-$$.msg.txt"

printf '%s\n' "$MESSAGE" > "$msg_file"

echo "queued=1"
echo "file=$msg_file"
echo "chars=$(printf '%s' "$MESSAGE" | wc -c | tr -d ' ')"
