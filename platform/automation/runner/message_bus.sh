#!/usr/bin/env bash

runner_message_bus_enabled() {
  local enabled="${1:-1}"
  local script_path="${2:-}"
  [[ "$enabled" == "1" && -n "$script_path" && -x "$script_path" ]]
}
