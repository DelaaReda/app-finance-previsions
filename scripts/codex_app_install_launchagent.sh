#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  codex_app_install_launchagent.sh [options]

Options:
      --label LABEL         Label launchd (defaut: com.venom.codex-app-injector)
      --interval SEC        StartInterval en secondes (defaut: 45)
      --state-dir PATH      Dossier etat (defaut: runtime/codex-app-automation)
      --app-name NAME       Nom app macOS (defaut: Codex)
      --chat-mode MODE      same|new (defaut: same)
      --max N               Max messages par run worker (defaut: 3)
      --focus-wait SEC      Delai activation app (defaut: 1.0)
      --post-wait SEC       Delai post injection (defaut: 0.4)
      --dry-run             Affiche le plist sans charger
  -h, --help               Affiche cette aide
USAGE
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="${CODEX_LAUNCHD_LABEL:-com.venom.codex-app-injector}"
INTERVAL="${CODEX_LAUNCHD_INTERVAL_SECONDS:-45}"
STATE_DIR="${CODEX_APP_AUTOMATION_DIR:-$ROOT/runtime/codex-app-automation}"
APP_NAME="${CODEX_APP_NAME:-Codex}"
CHAT_MODE="${CHAT_MODE:-same}"
MAX_PER_RUN="${MAX_MESSAGES_PER_RUN:-3}"
FOCUS_WAIT="${FOCUS_WAIT_SECONDS:-1.0}"
POST_WAIT="${POST_WAIT_SECONDS:-0.4}"
DRY_RUN=0

while (($#)); do
  case "$1" in
    --label) shift; LABEL="${1:-}" ;;
    --interval) shift; INTERVAL="${1:-}" ;;
    --state-dir) shift; STATE_DIR="${1:-}" ;;
    --app-name) shift; APP_NAME="${1:-}" ;;
    --chat-mode) shift; CHAT_MODE="${1:-}" ;;
    --max) shift; MAX_PER_RUN="${1:-}" ;;
    --focus-wait) shift; FOCUS_WAIT="${1:-}" ;;
    --post-wait) shift; POST_WAIT="${1:-}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only" >&2; exit 2; }
[[ "$INTERVAL" =~ ^[0-9]+$ ]] || { echo "--interval must be integer" >&2; exit 2; }
[[ "$MAX_PER_RUN" =~ ^[0-9]+$ ]] || { echo "--max must be integer" >&2; exit 2; }
[[ "$INTERVAL" -ge 5 ]] || { echo "--interval must be >= 5" >&2; exit 2; }
[[ "$MAX_PER_RUN" -ge 1 ]] || { echo "--max must be >= 1" >&2; exit 2; }

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
UID_VALUE="$(id -u)"
PLIST_WRITE_PATH="$PLIST_PATH"
if [[ "$DRY_RUN" -eq 1 ]]; then
  PLIST_WRITE_PATH="/tmp/${LABEL}.$$.plist"
fi

mkdir -p "$PLIST_DIR" "$STATE_DIR"

cat > "$PLIST_WRITE_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>$ROOT/scripts/codex_app_queue_worker.sh</string>
      <string>--state-dir</string>
      <string>$STATE_DIR</string>
      <string>--app-name</string>
      <string>$APP_NAME</string>
      <string>--chat-mode</string>
      <string>$CHAT_MODE</string>
      <string>--max</string>
      <string>$MAX_PER_RUN</string>
      <string>--focus-wait</string>
      <string>$FOCUS_WAIT</string>
      <string>--post-wait</string>
      <string>$POST_WAIT</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>StartInterval</key>
    <integer>$INTERVAL</integer>

    <key>StandardOutPath</key>
    <string>$STATE_DIR/launchd.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$STATE_DIR/launchd.stderr.log</string>
  </dict>
</plist>
PLIST

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry_run=1"
  echo "plist=$PLIST_PATH"
  sed -n '1,220p' "$PLIST_WRITE_PATH"
  rm -f "$PLIST_WRITE_PATH"
  exit 0
fi

launchctl bootout "gui/$UID_VALUE/$LABEL" 2>/dev/null || true
launchctl enable "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID_VALUE" "$PLIST_PATH"
launchctl enable "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1 || true

echo "installed=1"
echo "label=$LABEL"
echo "plist=$PLIST_PATH"
echo "interval=$INTERVAL"
echo "state_dir=$STATE_DIR"
