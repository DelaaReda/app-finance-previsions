#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${OPENCLAW_CONFIG_FILE:-$HOME/.openclaw/openclaw.json}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${OPENCLAW_CONFIG_LOCK_BACKUP_DIR:-$HOME/.openclaw/snapshots/config-lock-$TS}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: config file not found: $CONFIG_FILE" >&2
  exit 2
fi

mkdir -p "$BACKUP_DIR"
cp -a "$CONFIG_FILE" "$BACKUP_DIR/openclaw.json" >/dev/null 2>&1 || true

# Apply immutable bit (requires sudo)
sudo chattr +i "$CONFIG_FILE"

echo "OK locked=$CONFIG_FILE backup=$BACKUP_DIR/openclaw.json"
lsattr "$CONFIG_FILE" || true
