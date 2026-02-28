#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${OPENCLAW_CONFIG_FILE:-$HOME/.openclaw/openclaw.json}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: config file not found: $CONFIG_FILE" >&2
  exit 2
fi

# Remove immutable bit (requires sudo)
sudo chattr -i "$CONFIG_FILE"

echo "OK unlocked=$CONFIG_FILE"
lsattr "$CONFIG_FILE" || true
