#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

BOARD_FILE="${PARALLEL_BOARD_FILE:-docs/orchestrator-ops/parallel-workstreams.json}"
MAP_FILE="${PARALLEL_ROLE_MAP_FILE:-docs/orchestrator-ops/parallel-role-cron-map.json}"

checks_total=0
checks_ok=0

check_ok() {
  checks_total=$((checks_total + 1))
  checks_ok=$((checks_ok + 1))
  printf 'CHECK_OK %s\n' "$1"
}

check_fail() {
  checks_total=$((checks_total + 1))
  printf 'CHECK_FAIL %s\n' "$1"
}

if bash -n scripts/cron_tmux_role_runner.sh; then
  check_ok "bash_syntax:cron_tmux_role_runner"
else
  check_fail "bash_syntax:cron_tmux_role_runner"
fi

if bash -n scripts/configure_parallel_team_crons.sh; then
  check_ok "bash_syntax:configure_parallel_team_crons"
else
  check_fail "bash_syntax:configure_parallel_team_crons"
fi

if bash -n scripts/stale_cron_sweep.sh; then
  check_ok "bash_syntax:stale_cron_sweep"
else
  check_fail "bash_syntax:stale_cron_sweep"
fi

if bash -n scripts/stale_cron_tick.sh; then
  check_ok "bash_syntax:stale_cron_tick"
else
  check_fail "bash_syntax:stale_cron_tick"
fi

if bash -n scripts/tmux_codex_live_monitor.sh; then
  check_ok "bash_syntax:tmux_codex_live_monitor"
else
  check_fail "bash_syntax:tmux_codex_live_monitor"
fi

if bash -n scripts/tmux_live_watchdog.sh; then
  check_ok "bash_syntax:tmux_live_watchdog"
else
  check_fail "bash_syntax:tmux_live_watchdog"
fi

if python3 -m py_compile scripts/parallel_workstream.py; then
  check_ok "python_compile:parallel_workstream"
else
  check_fail "python_compile:parallel_workstream"
fi

if [[ ! -f "$BOARD_FILE" ]]; then
  scripts/parallel_workstream.py --board "$BOARD_FILE" init >/dev/null
fi

if scripts/parallel_workstream.py --board "$BOARD_FILE" validate >/dev/null; then
  check_ok "board_validate"
else
  check_fail "board_validate"
fi

if [[ -f "$MAP_FILE" ]]; then
  cron_json="$(openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  missing_roles="$(jq -r --argjson jobs "$cron_json" '
    [
      .roles[]?
      | select((.provisioned // 0) == 1)
      | select((.id // "") != "")
      | select(([$jobs.jobs[]?.id] | index(.id)) | not)
      | .role
    ] | if length==0 then "" else join(",") end
  ' "$MAP_FILE" 2>/dev/null || true)"
  if [[ -z "$missing_roles" ]]; then
    check_ok "role_map_ids_present"
  else
    check_fail "role_map_ids_present missing_roles=${missing_roles}"
  fi

  missing_utility_jobs="$(jq -r --argjson jobs "$cron_json" '
    [
      .utility_jobs[]?
      | select((.provisioned // 0) == 1)
      | select((.id // "") != "")
      | select(([$jobs.jobs[]?.id] | index(.id)) | not)
      | .name
    ] | if length==0 then "" else join(",") end
  ' "$MAP_FILE" 2>/dev/null || true)"
  if [[ -z "$missing_utility_jobs" ]]; then
    check_ok "utility_map_ids_present"
  else
    check_fail "utility_map_ids_present missing_jobs=${missing_utility_jobs}"
  fi
else
  check_fail "role_map_missing path=${MAP_FILE}"
fi

failed=$((checks_total - checks_ok))
printf 'PARALLEL_PLUMBING_SUMMARY total=%s ok=%s failed=%s board=%s map=%s\n' "$checks_total" "$checks_ok" "$failed" "$BOARD_FILE" "$MAP_FILE"
if [[ "$failed" -gt 0 ]]; then
  exit 2
fi
