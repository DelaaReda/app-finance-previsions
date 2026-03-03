#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-$HOME/.config/Claude}"
BASE_DESKTOP_CONFIG="${BASE_DESKTOP_CONFIG:-$BASE_DIR/claude_desktop_config.json}"
BASE_APP_CONFIG="${BASE_APP_CONFIG:-$BASE_DIR/config.json}"

usage() {
  cat <<'EOF'
Usage:
  scripts/claude_desktop_apply_mcp_to_profiles.sh [profile_dir...]

Default target profiles:
  ~/.claude-profile-1
  ~/.claude-profile-2
  ~/.claude-profile-3

Behavior:
  - Merge base mcpServers into each profile's claude_desktop_config.json
  - Force mcpServers.*.alwaysAllow=true
  - Set preferences.bypassPermissionsModeEnabled=true in:
      - claude_desktop_config.json
      - config.json
  - Create timestamped backups before writing
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Missing dependency: jq" >&2
  exit 127
fi

if [[ ! -f "${BASE_DESKTOP_CONFIG}" ]]; then
  echo "Missing base desktop config: ${BASE_DESKTOP_CONFIG}" >&2
  exit 2
fi

if [[ ! -f "${BASE_APP_CONFIG}" ]]; then
  echo "Missing base app config: ${BASE_APP_CONFIG}" >&2
  exit 2
fi

if (($# > 0)); then
  PROFILES=("$@")
else
  PROFILES=(
    "$HOME/.claude-profile-1"
    "$HOME/.claude-profile-2"
    "$HOME/.claude-profile-3"
  )
fi

MCP_JSON="$(jq -c '.mcpServers // {}' "${BASE_DESKTOP_CONFIG}")"
stamp="$(date +%Y%m%d-%H%M%S)"

for profile in "${PROFILES[@]}"; do
  mkdir -p "${profile}"

  desktop_cfg="${profile}/claude_desktop_config.json"
  app_cfg="${profile}/config.json"

  [[ -f "${desktop_cfg}" ]] || echo '{}' > "${desktop_cfg}"
  [[ -f "${app_cfg}" ]] || echo '{}' > "${app_cfg}"

  tmp_desktop="$(mktemp /tmp/claude-prof-desktop.XXXXXX.json)"
  tmp_app="$(mktemp /tmp/claude-prof-app.XXXXXX.json)"

  jq --argjson mcp "${MCP_JSON}" '
    .mcpServers = (((.mcpServers // {}) + ($mcp // {}))
      | with_entries(
          if (.value | type) == "object" then
            .value = (.value + {"alwaysAllow": true})
          else
            .
          end
        )
    )
    | .preferences = ((.preferences // {}) + {"bypassPermissionsModeEnabled": true})
  ' "${desktop_cfg}" > "${tmp_desktop}"

  jq '
    .preferences = ((.preferences // {}) + {"bypassPermissionsModeEnabled": true})
  ' "${app_cfg}" > "${tmp_app}"

  cp "${desktop_cfg}" "${desktop_cfg}.bak.${stamp}"
  cp "${app_cfg}" "${app_cfg}.bak.${stamp}"
  mv "${tmp_desktop}" "${desktop_cfg}"
  mv "${tmp_app}" "${app_cfg}"

  echo "updated=${profile}"
done
