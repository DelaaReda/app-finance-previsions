#!/usr/bin/env bash

# Echo 3 values separated by '|': CODEX_EXEC_AVAILABLE|CODEX_EXEC_PRIMARY|PRIMARY_CHANNEL
runner_pick_primary_channel() {
  local agent_bin_name="${1:-codex}"
  local codex_exec_fallback="${2:-1}"
  local retry_engine_default="${3:-sdk}"
  local role="${4:-unknown}"

  local codex_exec_available=0
  local codex_exec_primary=0
  local primary_channel="tmux"

  if [[ "$agent_bin_name" == "codex" && "$codex_exec_fallback" == "1" ]]; then
    codex_exec_available=1
  fi

  if [[ "$codex_exec_available" -eq 1 && "$retry_engine_default" == "sdk" ]]; then
    case "$role" in
      planner|dev|admin|scrum_master)
        codex_exec_primary=1
        primary_channel="codex_exec"
        ;;
      *)
        ;;
    esac
  fi

  printf '%s|%s|%s\n' "$codex_exec_available" "$codex_exec_primary" "$primary_channel"
}
