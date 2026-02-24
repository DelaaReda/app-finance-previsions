#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.githooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "❌ Missing hooks directory: $HOOKS_DIR"
  exit 1
fi

chmod +x "$HOOKS_DIR"/*
git -C "$ROOT_DIR" config core.hooksPath .githooks

echo "✅ Git hooks installed"
echo "   core.hooksPath=$(git -C "$ROOT_DIR" config --get core.hooksPath)"
echo "   hooks: $(ls -1 "$HOOKS_DIR" | tr '\n' ' ')"
