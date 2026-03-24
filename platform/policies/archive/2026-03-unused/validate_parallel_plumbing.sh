#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

PLUMBING_BOARD_FILE="${PARALLEL_PLUMBING_BOARD_FILE:-logs-codex-runs/orchestrator-state/parallel-workstreams.json}"
BOARD_FILE="${PARALLEL_BOARD_FILE:-$PLUMBING_BOARD_FILE}"
MAP_FILE="${PARALLEL_ROLE_MAP_FILE:-logs-codex-runs/orchestrator-state/parallel-role-cron-map.json}"
ALLOWED_EXTRA_CRON_NAMES="${PARALLEL_ALLOWED_EXTRA_CRON_NAMES:-}"

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

if bash -n scripts/orchestration_circuit_breaker.sh; then
  check_ok "bash_syntax:orchestration_circuit_breaker"
else
  check_fail "bash_syntax:orchestration_circuit_breaker"
fi

if bash -n scripts/export_orchestration_kpi.sh; then
  check_ok "bash_syntax:export_orchestration_kpi"
else
  check_fail "bash_syntax:export_orchestration_kpi"
fi

if bash -n scripts/dg_monitor_tick.sh; then
  check_ok "bash_syntax:dg_monitor_tick"
else
  check_fail "bash_syntax:dg_monitor_tick"
fi

if bash -n scripts/dg_alert_15m.sh; then
  check_ok "bash_syntax:dg_alert_15m"
else
  check_fail "bash_syntax:dg_alert_15m"
fi

if python3 -m py_compile platform/automation/compat/projections/parallel_workstream.py; then
  check_ok "python_compile:parallel_workstream"
else
  check_fail "python_compile:parallel_workstream"
fi

if [[ ! -f "$BOARD_FILE" ]]; then
  platform/automation/compat/projections/parallel_workstream.py --board "$BOARD_FILE" init >/dev/null
fi

if platform/automation/compat/projections/parallel_workstream.py --board "$BOARD_FILE" validate >/dev/null; then
  check_ok "board_validate"
else
  check_fail "board_validate"
fi

if [[ -f "logs-codex-runs/orchestrator-state/executors-monitoring-latest.json" ]] \
  && jq -e '.summary.roles_total != null and .summary.issues_open != null and .summary.blockers_open != null and .summary.tool_skill_requests_open != null' \
      logs-codex-runs/orchestrator-state/executors-monitoring-latest.json >/dev/null 2>&1; then
  check_ok "executors_monitoring_latest_json"
else
  check_fail "executors_monitoring_latest_json"
fi

if [[ -f "$MAP_FILE" ]]; then
  cron_json="$(openclaw cron list --all --json 2>/dev/null || openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
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

  missing_expected_jobs="$(jq -r --argjson jobs "$cron_json" '
    (
      [ .roles[]? | select((.provisioned // 0) == 1) | .name ]
      + [ .utility_jobs[]? | select((.provisioned // 0) == 1) | .name ]
      + ["adminapp-codex-sync-10m", "admin-agents-supervisor-15m"]
    ) as $expected
    | ([ $jobs.jobs[]?.name ] | unique) as $actual
    | [ $expected[] | select((($actual | index(.)) == null)) ]
    | if length==0 then "" else join(",") end
  ' "$MAP_FILE" 2>/dev/null || true)"
  if [[ -z "$missing_expected_jobs" ]]; then
    check_ok "expected_job_names_present"
  else
    check_fail "expected_job_names_present missing_jobs=${missing_expected_jobs}"
  fi

  unexpected_jobs="$(jq -r --argjson jobs "$cron_json" '
    (
      [ .roles[]? | select((.provisioned // 0) == 1) | .name ]
      + [ .utility_jobs[]? | select((.provisioned // 0) == 1) | .name ]
      + ["adminapp-codex-sync-10m", "admin-agents-supervisor-15m"]
    ) as $expected
    | [ $jobs.jobs[]?.name | select((($expected | index(.)) == null)) ]
    | if length==0 then "" else join(",") end
  ' "$MAP_FILE" 2>/dev/null || true)"
  if [[ -n "$unexpected_jobs" && -n "$ALLOWED_EXTRA_CRON_NAMES" ]]; then
    filtered_unexpected=""
    IFS=',' read -r -a _unexpected_arr <<< "$unexpected_jobs"
    IFS=',' read -r -a _allowed_arr <<< "$ALLOWED_EXTRA_CRON_NAMES"
    for _u in "${_unexpected_arr[@]}"; do
      _u="${_u#"${_u%%[![:space:]]*}"}"
      _u="${_u%"${_u##*[![:space:]]}"}"
      [[ -z "$_u" ]] && continue
      _allowed=0
      for _a in "${_allowed_arr[@]}"; do
        _a="${_a#"${_a%%[![:space:]]*}"}"
        _a="${_a%"${_a##*[![:space:]]}"}"
        if [[ "$_u" == "$_a" ]]; then
          _allowed=1
          break
        fi
      done
      if [[ "$_allowed" -eq 0 ]]; then
        if [[ -n "$filtered_unexpected" ]]; then
          filtered_unexpected="${filtered_unexpected},${_u}"
        else
          filtered_unexpected="${_u}"
        fi
      fi
    done
    unexpected_jobs="$filtered_unexpected"
  fi
  if [[ -z "$unexpected_jobs" ]]; then
    check_ok "unexpected_job_names_absent"
  else
    check_fail "unexpected_job_names_absent unexpected_jobs=${unexpected_jobs}"
  fi

  role_policy_drift="$(jq -r --argjson jobs "$cron_json" '
    [
      .roles[]?
      | select((.provisioned // 0) == 1)
      | . as $r
      | (
          ($jobs.jobs[]? | select(.id == $r.id)) //
          ($jobs.jobs[]? | select(.name == $r.name))
        ) as $j
      | if $j == null then
          "missing_job:\($r.role)"
        else
          (
            []
            + (if (($j.payload.timeoutSeconds // -1) != ($r.timeout_seconds // -1))
               then ["timeout_mismatch:\($r.role):expected=\($r.timeout_seconds // "none"):actual=\($j.payload.timeoutSeconds // "none")"] else [] end)
            + (if (($j.payload.thinking // "") != ($r.thinking // ""))
               then ["thinking_mismatch:\($r.role):expected=\($r.thinking // "none"):actual=\($j.payload.thinking // "none")"] else [] end)
            + (if (($j.payload.message // "") | contains("bash scripts/cron_tmux_role_runner.sh \($r.role)") | not)
               then ["runner_payload_missing:\($r.role)"] else [] end)
            + (if ((($j.payload.message // "") | contains("TMUX_ROLE_AGENT_BIN=codex") | not) && (($j.payload.message // "") | contains("TMUX_ROLE_AGENT_BIN=qwen") | not))
               then ["agent_bin_mismatch:\($r.role)"] else [] end)
            + (if (($j.payload.message // "") | contains("TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk") | not)
               then ["retry_engine_mismatch:\($r.role)"] else [] end)
            + (if (($j.payload.message // "") | contains("PROMPT_TIMEOUT_SECONDS=180") | not)
               then ["prompt_timeout_mismatch:\($r.role)"] else [] end)
            + (if (($j.payload.message // "") | contains("RETRY_PROMPT_TIMEOUT_SECONDS=90") | not)
               then ["retry_timeout_mismatch:\($r.role)"] else [] end)
            + (if (($j.payload.message // "") | contains("TMUX_ROLE_STALL_ABORT_SECONDS=75") | not)
               then ["stall_abort_mismatch:\($r.role)"] else [] end)
          )[]
        end
    ] | if length==0 then "" else join(",") end
  ' "$MAP_FILE" 2>/dev/null || true)"
  if [[ -z "$role_policy_drift" ]]; then
    check_ok "role_policy_parity"
  else
    check_fail "role_policy_parity drift=${role_policy_drift}"
  fi
else
  check_fail "role_map_missing path=${MAP_FILE}"
fi

failed=$((checks_total - checks_ok))
printf 'PARALLEL_PLUMBING_SUMMARY total=%s ok=%s failed=%s board=%s map=%s\n' "$checks_total" "$checks_ok" "$failed" "$BOARD_FILE" "$MAP_FILE"
if [[ "$failed" -gt 0 ]]; then
  exit 2
fi
