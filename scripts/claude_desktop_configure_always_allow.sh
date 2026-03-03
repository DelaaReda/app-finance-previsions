#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CLAUDE_DESKTOP_CONFIG_PATH:-$HOME/.config/Claude/claude_desktop_config.json}"
BACKUP_DIR="${CLAUDE_DESKTOP_CONFIG_BACKUP_DIR:-$HOME/.config/Claude}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  scripts/claude_desktop_configure_always_allow.sh [--config PATH] [--dry-run]

Purpose:
  Force mcpServers.*.alwaysAllow=true in Claude Desktop config
  to avoid repeated authorization prompts.

Options:
  --config PATH   Override config path (default: ~/.config/Claude/claude_desktop_config.json)
  --dry-run       Show resulting config without writing
  -h, --help      Show this help
EOF
}

while (($#)); do
  case "$1" in
    --config)
      shift
      if (($# == 0)); then
        echo "Missing value for --config" >&2
        exit 2
      fi
      CONFIG_PATH="$1"
      ;;
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

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Config file not found: ${CONFIG_PATH}" >&2
  exit 2
fi

tmp_out="$(mktemp /tmp/claude-config-allow.XXXXXX.json)"
cleanup() {
  rm -f "${tmp_out}"
}
trap cleanup EXIT

jq '
  if (.mcpServers | type) != "object" then
    .
  else
    .mcpServers |= with_entries(
      if (.value | type) == "object" then
        .value = (.value + {"alwaysAllow": true})
      else
        .
      end
    )
  end
' "${CONFIG_PATH}" > "${tmp_out}"

if (( DRY_RUN == 1 )); then
  cat "${tmp_out}"
  echo
  echo "dry_run=1"
  echo "config=${CONFIG_PATH}"
  exit 0
fi

mkdir -p "${BACKUP_DIR}"
stamp="$(date +%Y%m%d-%H%M%S)"
backup_path="${BACKUP_DIR}/claude_desktop_config.json.bak.${stamp}"
cp "${CONFIG_PATH}" "${backup_path}"
mv "${tmp_out}" "${CONFIG_PATH}"

echo "config_updated=1"
echo "config=${CONFIG_PATH}"
echo "backup=${backup_path}"
echo "servers:"
jq -r '
  if (.mcpServers | type) != "object" then
    "  (none)"
  else
    .mcpServers
    | to_entries[]
    | "  \(.key)=\(.value.alwaysAllow // false)"
  end
' "${CONFIG_PATH}"
echo "restart_required=1"
echo "restart_hint=close_and_reopen_claude_desktop"
