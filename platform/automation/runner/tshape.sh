#!/usr/bin/env bash

runner_tshape_targets_csv() {
  local raw="${TMUX_ROLE_ADMIN_TSHAPE_ALLOWED_TARGETS:-planner,dev}"
  printf '%s\n' "$raw"
}

runner_tshape_has_target() {
  local needle="${1:-}"
  local csv
  csv="$(runner_tshape_targets_csv)"
  IFS=',' read -r -a targets <<< "$csv"
  local item=""
  for item in "${targets[@]}"; do
    if [[ "$(echo "$item" | xargs)" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}
