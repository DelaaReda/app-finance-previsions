#!/usr/bin/env bash
set -euo pipefail

echo "[share] Stopping ngrok processes…"
pkill -f "ngrok start --all" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
echo "[share] Done."

