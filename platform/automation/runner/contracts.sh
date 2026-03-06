#!/usr/bin/env bash

runner_contract_value_from_text() {
  local key="$1"
  local text="$2"
  printf '%s\n' "$text" \
    | tr -d '\r' \
    | sed -n "s/^.*${key}:[[:space:]]*//p" \
    | head -1 \
    | sed 's/[[:space:]]*$//'
}

runner_contract_value_from_file() {
  local key="$1"
  local file="$2"
  [[ -f "$file" ]] || return 0
  sed -n "s/^${key}:[[:space:]]*//p" "$file" | head -1 | tr -d '\r' | sed 's/[[:space:]]*$//'
}

runner_contract_is_blocked() {
  local status="${1:-}"
  local verdict="${2:-}"
  [[ "${status^^}" == "BLOCKED" || "${verdict^^}" == "BLOCKED" ]]
}
