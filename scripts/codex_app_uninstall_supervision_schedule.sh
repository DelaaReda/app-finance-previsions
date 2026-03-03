#!/usr/bin/env bash
set -euo pipefail

UID_VALUE="$(id -u)"
WORKER_LABEL="${1:-com.venom.codex-app-injector}"
SCHED_LABEL="${2:-com.venom.codex-app-supervision-enqueue}"
PLIST_DIR="$HOME/Library/LaunchAgents"

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only" >&2; exit 2; }

for label in "$SCHED_LABEL" "$WORKER_LABEL"; do
  launchctl bootout "gui/$UID_VALUE/$label" 2>/dev/null || true
  launchctl disable "gui/$UID_VALUE/$label" >/dev/null 2>&1 || true
  plist="$PLIST_DIR/$label.plist"
  [[ -f "$plist" ]] && rm -f "$plist"
  echo "removed_label=$label"
done

echo "uninstalled=1"
