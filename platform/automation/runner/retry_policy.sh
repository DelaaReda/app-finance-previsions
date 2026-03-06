#!/usr/bin/env bash

runner_should_skip_tmux_retry() {
  local primary_channel="${1:-tmux}"
  local codex_exec_available="${2:-0}"
  local skip_tmux_retry_if_codex="${3:-1}"
  [[ "$primary_channel" == "tmux" && "$codex_exec_available" == "1" && "$skip_tmux_retry_if_codex" == "1" ]]
}
