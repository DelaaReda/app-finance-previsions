#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.config/Claude}"
DESKTOP_CONFIG="${DESKTOP_CONFIG:-$CLAUDE_DIR/claude_desktop_config.json}"
APP_CONFIG="${APP_CONFIG:-$CLAUDE_DIR/config.json}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  scripts/claude_desktop_enable_yolo_mode.sh [--dry-run]

Purpose:
  Reduce Claude Desktop permission prompts as much as possible by:
  1) forcing mcpServers.*.alwaysAllow=true
  2) enabling preferences.bypassPermissionsModeEnabled=true

Files touched:
  ~/.config/Claude/claude_desktop_config.json
  ~/.config/Claude/config.json

Options:
  --dry-run   Print computed JSON changes without writing files
  -h, --help  Show this help
EOF
}

while (($#)); do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if ! command -v jq >/dev/null 2>&1; then
  echo "Missing dependency: jq" >&2
  exit 127
fi

if [[ ! -f "${DESKTOP_CONFIG}" ]]; then
  echo "Missing file: ${DESKTOP_CONFIG}" >&2
  exit 2
fi

if [[ ! -f "${APP_CONFIG}" ]]; then
  echo "Missing file: ${APP_CONFIG}" >&2
  exit 2
fi

tmp_desktop="$(mktemp /tmp/claude-desktop-yolo.desktop.XXXXXX.json)"
tmp_app="$(mktemp /tmp/claude-desktop-yolo.app.XXXXXX.json)"
cleanup() {
  rm -f "${tmp_desktop}" "${tmp_app}"
}
trap cleanup EXIT

jq '
  if (.mcpServers | type) == "object" then
    .mcpServers |= with_entries(
      if (.value | type) == "object" then
        .value = (.value + {"alwaysAllow": true})
      else
        .
      end
    )
  else
    .
  end
  | .preferences = ((.preferences // {}) + {"bypassPermissionsModeEnabled": true})
' "${DESKTOP_CONFIG}" > "${tmp_desktop}"

jq '
  .preferences = ((.preferences // {}) + {"bypassPermissionsModeEnabled": true})
' "${APP_CONFIG}" > "${tmp_app}"

if (( DRY_RUN == 1 )); then
  echo "desktop_config=${DESKTOP_CONFIG}"
  cat "${tmp_desktop}"
  echo
  echo "app_config=${APP_CONFIG}"
  cat "${tmp_app}"
  echo
  echo "dry_run=1"
  exit 0
fi

stamp="$(date +%Y%m%d-%H%M%S)"
backup_desktop="${DESKTOP_CONFIG}.bak.${stamp}"
backup_app="${APP_CONFIG}.bak.${stamp}"
cp "${DESKTOP_CONFIG}" "${backup_desktop}"
cp "${APP_CONFIG}" "${backup_app}"

mv "${tmp_desktop}" "${DESKTOP_CONFIG}"
mv "${tmp_app}" "${APP_CONFIG}"

echo "yolo_mode_enabled=1"
echo "desktop_config=${DESKTOP_CONFIG}"
echo "desktop_backup=${backup_desktop}"
echo "app_config=${APP_CONFIG}"
echo "app_backup=${backup_app}"
echo "mcp_servers:"
jq -r '
  if (.mcpServers | type) != "object" then
    "  (none)"
  else
    .mcpServers
    | to_entries[]
    | "  \(.key)=\(.value.alwaysAllow // false)"
  end
' "${DESKTOP_CONFIG}"
echo "desktop_bypassPermissionsModeEnabled=$(jq -r '.preferences.bypassPermissionsModeEnabled // false' "${DESKTOP_CONFIG}")"
echo "app_bypassPermissionsModeEnabled=$(jq -r '.preferences.bypassPermissionsModeEnabled // false' "${APP_CONFIG}")"
echo "restart_required=1"
echo "restart_hint=close_and_reopen_claude_desktop"
