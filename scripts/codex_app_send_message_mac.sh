#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  codex_app_send_message_mac.sh --message "text" [options]
  codex_app_send_message_mac.sh --message-file /path/msg.txt [options]
  codex_app_send_message_mac.sh --stdin [options]

Options:
  -m, --message TEXT        Message a injecter
      --message-file PATH   Fichier message
      --stdin               Lire le message depuis stdin
      --app-name NAME       Nom app macOS (defaut: Codex)
      --chat-mode MODE      same|new (defaut: same)
      --no-return           Ne pas envoyer Entrer
      --focus-wait SEC      Delai activation app (defaut: 1.0)
      --post-wait SEC       Delai apres injection (defaut: 0.4)
      --dry-run             N'injecte rien, affiche seulement
  -h, --help                Affiche cette aide

Notes:
  - macOS uniquement
  - Requiert autorisation Accessibilite pour Terminal/Codex
USAGE
}

APP_NAME="${CODEX_APP_NAME:-Codex}"
CHAT_MODE="${CHAT_MODE:-same}"
SEND_RETURN=1
FOCUS_WAIT="${FOCUS_WAIT_SECONDS:-1.0}"
POST_WAIT="${POST_WAIT_SECONDS:-0.4}"
DRY_RUN=0
READ_STDIN=0
MESSAGE=""
MESSAGE_FILE=""

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
    --no-return)
      SEND_RETURN=0
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
    --dry-run)
      DRY_RUN=1
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

case "$CHAT_MODE" in
  same|new) ;;
  *) echo "invalid --chat-mode: $CHAT_MODE (expected same|new)" >&2; exit 2 ;;
esac

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS only: current OS is $(uname -s)" >&2
  exit 2
fi

if ! command -v osascript >/dev/null 2>&1; then
  echo "osascript not found" >&2
  exit 127
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'dry_run=1\napp=%s\nchat_mode=%s\nsend_return=%s\nmessage_chars=%s\n' \
    "$APP_NAME" "$CHAT_MODE" "$SEND_RETURN" "$(printf '%s' "$MESSAGE" | wc -c | tr -d ' ')"
  exit 0
fi

osascript - "$APP_NAME" "$MESSAGE" "$CHAT_MODE" "$SEND_RETURN" "$FOCUS_WAIT" "$POST_WAIT" <<'APPLESCRIPT'
on run argv
  set appName to item 1 of argv
  set messageText to item 2 of argv
  set chatMode to item 3 of argv
  set sendReturn to item 4 of argv
  set focusWait to (item 5 of argv) as real
  set postWait to (item 6 of argv) as real

  tell application appName
    activate
  end tell
  delay focusWait

  tell application "System Events"
    if not (exists process appName) then error "Process not found: " & appName

    tell process appName
      set frontmost to true

      if chatMode is "new" then
        keystroke "n" using {command down}
        delay 0.35
      end if

      -- Best-effort: many chat UIs keep the composer focused when frontmost.
      set the clipboard to messageText
      keystroke "v" using {command down}
      delay 0.15

      if sendReturn is "1" then
        key code 36
      end if
    end tell
  end tell

  delay postWait
  return "ok"
end run
APPLESCRIPT

printf 'sent=1\napp=%s\nchat_mode=%s\nmessage_chars=%s\n' \
  "$APP_NAME" "$CHAT_MODE" "$(printf '%s' "$MESSAGE" | wc -c | tr -d ' ')"
