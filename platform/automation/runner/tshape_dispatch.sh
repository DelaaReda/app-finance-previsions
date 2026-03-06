#!/usr/bin/env bash

runner_tshape_active_for_admin() {
  local role="${1:-}"
  local tshape_enabled="${2:-0}"
  [[ "$role" == "admin" && "$tshape_enabled" == "1" ]]
}
