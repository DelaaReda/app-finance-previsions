#!/usr/bin/env bash
set -euo pipefail

# Backward-compatible typo alias kept intentionally.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec "${SCRIPT_DIR}/message_to_planner.sh" "$@"
