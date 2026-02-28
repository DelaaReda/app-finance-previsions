#!/usr/bin/env bash
set -euo pipefail

LOCK_DIR="${OPENCLAW_CRON_LOCK_DIR:-/home/venom/.openclaw/cron}"
LOCK_FILE="${OPENCLAW_CRON_ADMIN_LOCK_FILE:-${LOCK_DIR}/admin-edit.lock}"
META_FILE="${LOCK_FILE}.meta"

mkdir -p "$LOCK_DIR"

if [[ "${1:-}" != "--" ]]; then
  echo "Usage: $0 -- <command...>" >&2
  exit 2
fi
shift

if [[ $# -eq 0 ]]; then
  echo "No command provided." >&2
  exit 2
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  holder="unknown"
  if [[ -f "$META_FILE" ]]; then
    holder="$(cat "$META_FILE" 2>/dev/null || true)"
  fi
  echo "ADMIN_LOCK_BUSY: ${holder}" >&2
  exit 73
fi

printf 'pid=%s host=%s time=%s cmd=%q\n' \
  "$$" \
  "$(hostname 2>/dev/null || echo unknown)" \
  "$(date -Is 2>/dev/null || date)" \
  "$*" >"$META_FILE"

"$@"
