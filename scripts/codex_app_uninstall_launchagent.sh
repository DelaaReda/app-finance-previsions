#!/usr/bin/env bash
set -euo pipefail

LABEL="${1:-com.venom.codex-app-injector}"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
UID_VALUE="$(id -u)"

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only" >&2; exit 2; }

launchctl bootout "gui/$UID_VALUE/$LABEL" 2>/dev/null || true
launchctl disable "gui/$UID_VALUE/$LABEL" >/dev/null 2>&1 || true

if [[ -f "$PLIST_PATH" ]]; then
  rm -f "$PLIST_PATH"
fi

echo "uninstalled=1"
echo "label=$LABEL"
echo "plist=$PLIST_PATH"
