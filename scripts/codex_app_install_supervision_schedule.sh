#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UID_VALUE="$(id -u)"
PLIST_DIR="$HOME/Library/LaunchAgents"

WORKER_LABEL="${WORKER_LABEL:-com.venom.codex-app-injector}"
SCHED_LABEL="${SCHED_LABEL:-com.venom.codex-app-supervision-enqueue}"
BUNDLE_DIR="${BUNDLE_DIR:-$HOME/.codex-app-automation}"
STATE_DIR="${CODEX_APP_AUTOMATION_DIR:-$BUNDLE_DIR/runtime/codex-app-automation}"
PROMPT_FILE="${PROMPT_FILE:-$ROOT/docs/ops/prompts/CODEX_SUPERVISION_SAME_PROMPT.txt}"
WORKER_INTERVAL="${WORKER_INTERVAL_SECONDS:-45}"
SCHEDULE_INTERVAL="${SCHEDULE_INTERVAL_SECONDS:-14400}"
CHAT_MODE="${CHAT_MODE:-same}"
MAX_PER_RUN="${MAX_MESSAGES_PER_RUN:-3}"
APP_NAME="${CODEX_APP_NAME:-Codex}"
FOCUS_WAIT="${FOCUS_WAIT_SECONDS:-1.0}"
POST_WAIT="${POST_WAIT_SECONDS:-0.4}"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage:
  codex_app_install_supervision_schedule.sh [options]

Options:
      --worker-interval SEC   Interval worker queue->Codex (defaut: 45)
      --schedule-interval SEC Interval supervision enqueue (defaut: 14400 = 4h)
      --bundle-dir PATH       Bundle local launchd (defaut: ~/.codex-app-automation)
      --state-dir PATH        Runtime state dir
      --prompt-file PATH      Prompt supervision source
      --chat-mode MODE        same|new (defaut: same)
      --max N                 Max messages traites par run worker
      --app-name NAME         Nom app desktop (defaut: Codex)
      --dry-run               Preview sans installer
  -h, --help                 Aide
USAGE
}

while (($#)); do
  case "$1" in
    --worker-interval) shift; WORKER_INTERVAL="${1:-}" ;;
    --schedule-interval) shift; SCHEDULE_INTERVAL="${1:-}" ;;
    --bundle-dir) shift; BUNDLE_DIR="${1:-}" ;;
    --state-dir) shift; STATE_DIR="${1:-}" ;;
    --prompt-file) shift; PROMPT_FILE="${1:-}" ;;
    --chat-mode) shift; CHAT_MODE="${1:-}" ;;
    --max) shift; MAX_PER_RUN="${1:-}" ;;
    --app-name) shift; APP_NAME="${1:-}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only" >&2; exit 2; }
[[ "$WORKER_INTERVAL" =~ ^[0-9]+$ ]] || { echo "worker interval must be integer" >&2; exit 2; }
[[ "$SCHEDULE_INTERVAL" =~ ^[0-9]+$ ]] || { echo "schedule interval must be integer" >&2; exit 2; }
[[ "$MAX_PER_RUN" =~ ^[0-9]+$ ]] || { echo "max must be integer" >&2; exit 2; }
[[ "$WORKER_INTERVAL" -ge 5 ]] || { echo "worker interval must be >= 5" >&2; exit 2; }
[[ "$SCHEDULE_INTERVAL" -ge 60 ]] || { echo "schedule interval must be >= 60" >&2; exit 2; }
[[ "$MAX_PER_RUN" -ge 1 ]] || { echo "max must be >= 1" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 2; }

BUNDLE_SCRIPTS="$BUNDLE_DIR/scripts"
BUNDLE_PROMPTS="$BUNDLE_DIR/prompts"
BUNDLE_PROMPT_FILE="$BUNDLE_PROMPTS/CODEX_SUPERVISION_SAME_PROMPT.txt"
WORKER_SCRIPT="$BUNDLE_SCRIPTS/codex_app_queue_worker.sh"
ENQUEUE_SCRIPT="$BUNDLE_SCRIPTS/codex_app_enqueue_supervision_prompt.sh"

mkdir -p "$PLIST_DIR" "$BUNDLE_SCRIPTS" "$BUNDLE_PROMPTS" "$STATE_DIR"

for src in \
  "$ROOT/scripts/codex_app_send_message_mac.sh" \
  "$ROOT/scripts/codex_app_enqueue_message.sh" \
  "$ROOT/scripts/codex_app_queue_worker.sh" \
  "$ROOT/scripts/codex_app_enqueue_supervision_prompt.sh"; do
  [[ -f "$src" ]] || { echo "missing source script: $src" >&2; exit 2; }
  cp "$src" "$BUNDLE_SCRIPTS/"
done
chmod +x "$BUNDLE_SCRIPTS"/*.sh
cp "$PROMPT_FILE" "$BUNDLE_PROMPT_FILE"

WORKER_PLIST="$PLIST_DIR/$WORKER_LABEL.plist"
SCHED_PLIST="$PLIST_DIR/$SCHED_LABEL.plist"
WORKER_WRITE="$WORKER_PLIST"
SCHED_WRITE="$SCHED_PLIST"
if [[ "$DRY_RUN" -eq 1 ]]; then
  WORKER_WRITE="/tmp/${WORKER_LABEL}.$$.plist"
  SCHED_WRITE="/tmp/${SCHED_LABEL}.$$.plist"
fi

cat > "$WORKER_WRITE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>$WORKER_LABEL</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>$WORKER_SCRIPT</string>
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
    <integer>$WORKER_INTERVAL</integer>

    <key>StandardOutPath</key>
    <string>$STATE_DIR/launchd.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$STATE_DIR/launchd.stderr.log</string>
  </dict>
</plist>
PLIST

cat > "$SCHED_WRITE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>$SCHED_LABEL</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>$ENQUEUE_SCRIPT</string>
      <string>--state-dir</string>
      <string>$STATE_DIR</string>
      <string>--prompt-file</string>
      <string>$BUNDLE_PROMPT_FILE</string>
      <string>--min-interval</string>
      <string>$SCHEDULE_INTERVAL</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>StartInterval</key>
    <integer>$SCHEDULE_INTERVAL</integer>

    <key>StandardOutPath</key>
    <string>$STATE_DIR/scheduler.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$STATE_DIR/scheduler.stderr.log</string>
  </dict>
</plist>
PLIST

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry_run=1"
  echo "bundle_dir=$BUNDLE_DIR"
  echo "state_dir=$STATE_DIR"
  echo "worker_label=$WORKER_LABEL"
  echo "scheduler_label=$SCHED_LABEL"
  echo "worker_plist=$WORKER_PLIST"
  echo "scheduler_plist=$SCHED_PLIST"
  sed -n '1,220p' "$WORKER_WRITE"
  sed -n '1,220p' "$SCHED_WRITE"
  rm -f "$WORKER_WRITE" "$SCHED_WRITE"
  exit 0
fi

for label in "$WORKER_LABEL" "$SCHED_LABEL"; do
  launchctl bootout "gui/$UID_VALUE/$label" 2>/dev/null || true
  launchctl enable "gui/$UID_VALUE/$label" >/dev/null 2>&1 || true
done

launchctl bootstrap "gui/$UID_VALUE" "$WORKER_PLIST"
launchctl bootstrap "gui/$UID_VALUE" "$SCHED_PLIST"

for label in "$WORKER_LABEL" "$SCHED_LABEL"; do
  launchctl enable "gui/$UID_VALUE/$label" >/dev/null 2>&1 || true
  launchctl kickstart -k "gui/$UID_VALUE/$label" >/dev/null 2>&1 || true
done

echo "installed=1"
echo "bundle_dir=$BUNDLE_DIR"
echo "state_dir=$STATE_DIR"
echo "worker_label=$WORKER_LABEL"
echo "scheduler_label=$SCHED_LABEL"
echo "worker_interval=$WORKER_INTERVAL"
echo "schedule_interval=$SCHEDULE_INTERVAL"
