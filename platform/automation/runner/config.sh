#!/usr/bin/env bash

runner_config_default_file() {
  local root="${1:-}"
  if [[ -n "$root" && -f "$root/platform/config/runner/runner.v1.yaml" ]]; then
    printf '%s\n' "$root/platform/config/runner/runner.v1.yaml"
    return 0
  fi
  if [[ -n "$root" && -f "$root/platform/automation/config/runner.v1.yaml" ]]; then
    printf '%s\n' "$root/platform/automation/config/runner.v1.yaml"
    return 0
  fi
  if [[ -n "$root" && -f "$root/platform/config/runner/runner_config.v1.yaml" ]]; then
    printf '%s\n' "$root/platform/config/runner/runner_config.v1.yaml"
    return 0
  fi
  printf '%s\n' "$root/platform/config/runner/runner.v1.yaml"
}

runner_config_default_loader() {
  local root="${1:-}"
  if [[ -n "$root" && -f "$root/platform/automation/runner_config.py" ]]; then
    printf '%s\n' "$root/platform/automation/runner_config.py"
    return 0
  fi
  if [[ -n "$root" && -f "$root/platform/automation/runner/config_loader.py" ]]; then
    printf '%s\n' "$root/platform/automation/runner/config_loader.py"
    return 0
  fi
  printf '%s\n' "$root/platform/automation/runner_config.py"
}

# runner_load_config_env ROLE CONFIG_FILE CONFIG_LOADER FALLBACK_ENV [LOG_FILE] [LOG_PREFIX]
runner_load_config_env() {
  local cfg_role="${1:-}"
  local cfg_file="${2:-}"
  local cfg_loader="${3:-}"
  local cfg_fallback="${4:-1}"
  local log_file="${5:-}"
  local log_prefix="${6:-RUNNER_CONFIG}"

  [[ -n "$cfg_role" ]] || return 2
  [[ -f "$cfg_file" ]] || return 0
  [[ -f "$cfg_loader" ]] || return 0
  command -v python3 >/dev/null 2>&1 || return 0

  local out_file err_file
  out_file="$(mktemp)"
  err_file="$(mktemp)"
  if ! python3 "$cfg_loader" \
      --config "$cfg_file" \
      emit-env \
      --role "$cfg_role" \
      --fallback-env "$cfg_fallback" >"$out_file" 2>"$err_file"; then
    local err_preview
    err_preview="$(tr '\n' ' ' <"$err_file" | sed 's/  */ /g' | cut -c1-220)"
    if [[ -n "$log_file" ]]; then
      printf '%s [%s] role=%s status=invalid file=%s detail=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$log_prefix" "$cfg_role" "$cfg_file" "$err_preview" >> "$log_file"
    else
      printf '[%s] role=%s status=invalid file=%s detail=%s\n' "$log_prefix" "$cfg_role" "$cfg_file" "$err_preview" >&2
    fi
    rm -f "$out_file" "$err_file"
    return 2
  fi

  while IFS= read -r kv; do
    [[ -n "$kv" ]] || continue
    [[ "$kv" == \#* ]] && continue
    eval "export $kv"
  done <"$out_file"

  if [[ -s "$err_file" ]]; then
    local warn_preview
    warn_preview="$(tr '\n' ' ' <"$err_file" | sed 's/  */ /g' | cut -c1-220)"
    if [[ -n "$log_file" ]]; then
      printf '%s [%s] role=%s status=fallback_env file=%s detail=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$log_prefix" "$cfg_role" "$cfg_file" "$warn_preview" >> "$log_file"
    fi
  else
    if [[ -n "$log_file" ]]; then
      printf '%s [%s] role=%s status=loaded file=%s fallback_env=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$log_prefix" "$cfg_role" "$cfg_file" "$cfg_fallback" >> "$log_file"
    fi
  fi

  rm -f "$out_file" "$err_file"
  return 0
}

runner_config_emit_env() {
  local cfg_role="${1:-}"
  local cfg_file="${2:-}"
  local cfg_loader="${3:-}"
  local cfg_fallback="${4:-1}"
  runner_load_config_env "$cfg_role" "$cfg_file" "$cfg_loader" "$cfg_fallback" "" "RUNNER_CONFIG"
}
