#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

OPENCLAW_BIN="${CRON_MANAGER_OPENCLAW_BIN:-}"
STALE_SWEEP_SCRIPT="${CRON_MANAGER_STALE_SWEEP_SCRIPT:-scripts/stale_cron_sweep.sh}"

usage() {
  cat <<'USAGE'
Usage: cron_run_manager.sh <command> [options]

Commands:
  status [--regex <jq_regex>] [--stale-threshold <seconds>]
      Show compact runtime status for cron jobs.

  pause --job <id|name|role>
      Disable one cron job.

  resume --job <id|name|role>
      Enable one cron job.

  stop-run --job <id|name|role>
           [--keep-disabled] [--no-session-kill] [--no-process-kill]
           [--reason <text>] [--dry-run]
      Stop an active run by disabling job, killing role process/session, and re-enabling by default.

  run-now --job <id|name|role> [--timeout <ms>] [--expect-final] [--no-expect-final]
      Trigger immediate run for one job.

  restart --job <id|name|role> [--timeout <ms>] [--expect-final] [--reason <text>]
      Stop current run and trigger a new one.

  last-summary --job <id|name|role> [--limit <n>]
      Print latest run summaries for one job.

  recover-stale [args passed to stale_cron_sweep.sh]
      Wrapper over scripts/stale_cron_sweep.sh.

Examples:
  bash scripts/cron_run_manager.sh status --stale-threshold 330
  bash scripts/cron_run_manager.sh pause --job planner
  bash scripts/cron_run_manager.sh resume --job planner
  bash scripts/cron_run_manager.sh stop-run --job planner --reason manual_stop
  bash scripts/cron_run_manager.sh run-now --job planner
  bash scripts/cron_run_manager.sh restart --job planner --expect-final --timeout 300000
  bash scripts/cron_run_manager.sh last-summary --job planner --limit 2
  bash scripts/cron_run_manager.sh recover-stale --dry-run --threshold 330
USAGE
}

require_jq() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required" >&2
    exit 5
  fi
}

resolve_openclaw_bin() {
  local candidate=""
  if [[ -n "$OPENCLAW_BIN" && -x "$OPENCLAW_BIN" ]]; then
    printf '%s\n' "$OPENCLAW_BIN"
    return 0
  fi
  for candidate in \
    "/home/venom/.npm-global/bin/openclaw" \
    "${HOME}/.npm-global/bin/openclaw" \
    "$(command -v openclaw 2>/dev/null || true)" \
    "/usr/local/bin/openclaw" \
    "/usr/bin/openclaw" \
    "/bin/openclaw"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

load_jobs_json() {
  JOBS_JSON="$("$OPENCLAW_BIN" cron list --all --json 2>/dev/null || "$OPENCLAW_BIN" cron list --json 2>/dev/null || echo '{"jobs":[]}')"
}

normalize_cron_runs_json() {
  local raw="${1:-}"
  if command -v python3 >/dev/null 2>&1 && [[ -f "${ROOT}/scripts/openclaw_cron_runs_normalize.py" ]]; then
    printf '%s' "$raw" | python3 "${ROOT}/scripts/openclaw_cron_runs_normalize.py" 2>/dev/null || echo '{"entries":[]}'
  else
    printf '%s' "$raw"
  fi
}

normalize_role() {
  local raw="$1"
  printf '%s' "$raw" | tr '-' '_' | tr '[:upper:]' '[:lower:]'
}

resolve_job_json() {
  local needle_raw="$1"
  local needle_role=""
  local needle_name=""
  local resolved=""

  needle_role="$(normalize_role "$needle_raw")"
  needle_name="$(printf '%s' "$needle_role" | tr '_' '-')"

  resolved="$(printf '%s' "$JOBS_JSON" | jq -c --arg v "$needle_raw" '[.jobs[]? | select(.id==$v)] | if length>0 then .[0] else empty end')"
  if [[ -n "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  resolved="$(printf '%s' "$JOBS_JSON" | jq -c --arg v "$needle_raw" '
    [ .jobs[]? | select(.name==$v) ] as $m
    | if ($m | length)==0 then empty
      elif ($m | length)==1 then $m[0]
      else
        ([$m[] | select(.enabled==true)] | if length>0 then (sort_by(.updatedAtMs // 0) | reverse | .[0]) else empty end)
        // ($m | sort_by(.updatedAtMs // 0) | reverse | .[0])
      end
  ')"
  if [[ -n "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  resolved="$(printf '%s' "$JOBS_JSON" | jq -c --arg role "$needle_role" --arg name "$needle_name" '
    [ .jobs[]? | select((.agentId // "") == $role or (.name // "") == ($name + "-tmux-loop")) ] as $m
    | if ($m | length)==0 then empty
      elif ($m | length)==1 then $m[0]
      else
        ([$m[] | select(.enabled==true)] | if length>0 then (sort_by(.updatedAtMs // 0) | reverse | .[0]) else empty end)
        // ($m | sort_by(.updatedAtMs // 0) | reverse | .[0])
      end
  ')"
  if [[ -n "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  echo "ERROR: no job found for '$needle_raw'" >&2
  exit 6
}

role_from_job_json() {
  local job_json="$1"
  printf '%s' "$job_json" | jq -r '
    (
      try ((.payload.message // "") | capture("cron_tmux_role_runner\\.sh (?<r>[A-Za-z0-9_]+)").r) catch ""
    ) as $r
    | if ($r != "") then $r
      elif ((.agentId // "") != "") then .agentId
      else ((.name // "unknown") | sub("-tmux-loop$";"") | gsub("-";"_"))
      end
  '
}

session_for_role() {
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    analyst) echo "codex_analyst_cron" ;;
    dev) echo "codex_dev_cron" ;;
    backend_engineer) echo "codex_backend_engineer_cron" ;;
    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
    integrator) echo "codex_integrator_cron" ;;
    data_analyst) echo "codex_data_analyst_cron" ;;
    infra_engineer) echo "codex_infra_engineer_cron" ;;
    tester) echo "codex_tester_cron" ;;
    qa) echo "codex_qa_cron" ;;
    architect) echo "codex_architect_cron" ;;
    po) echo "codex_po_cron" ;;
    scrum_master) echo "codex_scrum_master_cron" ;;
    clawsentinel) echo "clawsentinel" ;;
    admin-agents) echo "admin-agents-sync-cron" ;;
    adminapp-codex) echo "adminapp_codex_sync" ;;
    *) echo "" ;;
  esac
}

command_status() {
  local regex=".*"
  local stale_threshold="330"
  local now="0"
  local total="0"
  local enabled="0"
  local running="0"
  local stale="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --regex)
        regex="${2:-}"
        shift 2
        ;;
      --stale-threshold)
        stale_threshold="${2:-}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for status: $1" >&2
        exit 2
        ;;
    esac
  done

  if ! [[ "$stale_threshold" =~ ^[0-9]+$ ]] || [[ "$stale_threshold" -lt 1 ]]; then
    stale_threshold=330
  fi

  now="$(date -u +%s)"
  while IFS=$'\t' read -r id name agent enabled_flag running_ms last_status last_run_ms next_run_ms; do
    [[ -z "$id" ]] && continue
    total=$((total + 1))
    if [[ "$enabled_flag" == "true" ]]; then
      enabled=$((enabled + 1))
    fi

    local run_age="-"
    local is_running="0"
    local is_stale="0"

    if [[ "$running_ms" =~ ^[0-9]+$ ]]; then
      is_running=1
      running=$((running + 1))
      run_age="$((now - (running_ms / 1000)))"
      if [[ "$run_age" -ge "$stale_threshold" ]]; then
        is_stale=1
        stale=$((stale + 1))
      fi
    fi

    echo "CRON_STATUS id=${id} name=${name} agent=${agent:-none} enabled=${enabled_flag} running=${is_running} run_age_s=${run_age} stale=${is_stale} last_status=${last_status:-none} last_run_ms=${last_run_ms:-none} next_run_ms=${next_run_ms:-none}"
  done < <(
    printf '%s' "$JOBS_JSON" | jq -r --arg re "$regex" '
      .jobs[]? | select((.name // "") | test($re))
      | [
          .id,
          (.name // ""),
          (.agentId // ""),
          (.enabled // false),
          (.state.runningAtMs // "-"),
          (.state.lastStatus // .state.lastRunStatus // "none"),
          (.state.lastRunAtMs // "-"),
          (.state.nextRunAtMs // "-")
        ] | @tsv
    '
  )

  echo "CRON_STATUS_SUMMARY total=${total} enabled=${enabled} running=${running} stale=${stale} stale_threshold_s=${stale_threshold}"
}

command_last_summary() {
  local job_ref=""
  local limit="1"
  local job_json=""
  local job_id=""
  local job_name=""
  local runs_raw=""
  local runs_json=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --job)
        job_ref="${2:-}"
        shift 2
        ;;
      --limit)
        limit="${2:-}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for last-summary: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$job_ref" ]]; then
    echo "ERROR: --job is required" >&2
    exit 2
  fi
  if ! [[ "$limit" =~ ^[0-9]+$ ]] || [[ "$limit" -lt 1 ]]; then
    limit=1
  fi

  job_json="$(resolve_job_json "$job_ref")"
  job_id="$(printf '%s' "$job_json" | jq -r '.id')"
  job_name="$(printf '%s' "$job_json" | jq -r '.name')"

  runs_raw="$("$OPENCLAW_BIN" cron runs --id "$job_id" --limit "$limit" 2>/dev/null || echo '{}')"
  runs_json="$(normalize_cron_runs_json "$runs_raw")"
  printf '%s' "$runs_json" | jq -r --arg job "$job_name" '
    .entries[]?
    | "CRON_LAST_SUMMARY job=" + $job
      + " ts=" + ((.ts // 0) | tostring)
      + " status=" + (.status // "unknown")
      + " duration_ms=" + ((.durationMs // 0) | tostring)
      + " summary=" + ((((.summary // .error // "") | tostring) | gsub("[\n\r]+"; " | ")) // "")
  '
}

command_pause() {
  local job_ref=""
  local job_json=""
  local job_id=""
  local job_name=""
  local was_enabled=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --job)
        job_ref="${2:-}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for pause: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$job_ref" ]]; then
    echo "ERROR: --job is required" >&2
    exit 2
  fi

  job_json="$(resolve_job_json "$job_ref")"
  job_id="$(printf '%s' "$job_json" | jq -r '.id')"
  job_name="$(printf '%s' "$job_json" | jq -r '.name')"
  was_enabled="$(printf '%s' "$job_json" | jq -r '.enabled')"

  "$OPENCLAW_BIN" cron disable "$job_id" >/dev/null 2>&1 || true
  echo "PAUSE_RESULT job=${job_name} id=${job_id} was_enabled=${was_enabled}"
}

command_resume() {
  local job_ref=""
  local job_json=""
  local job_id=""
  local job_name=""
  local was_enabled=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --job)
        job_ref="${2:-}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for resume: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$job_ref" ]]; then
    echo "ERROR: --job is required" >&2
    exit 2
  fi

  job_json="$(resolve_job_json "$job_ref")"
  job_id="$(printf '%s' "$job_json" | jq -r '.id')"
  job_name="$(printf '%s' "$job_json" | jq -r '.name')"
  was_enabled="$(printf '%s' "$job_json" | jq -r '.enabled')"

  "$OPENCLAW_BIN" cron enable "$job_id" >/dev/null 2>&1 || true
  echo "RESUME_RESULT job=${job_name} id=${job_id} was_enabled=${was_enabled}"
}

command_run_now() {
  local job_ref=""
  local timeout_ms="300000"
  local expect_final=0
  local job_json=""
  local job_id=""
  local job_name=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --job)
        job_ref="${2:-}"
        shift 2
        ;;
      --timeout)
        timeout_ms="${2:-}"
        shift 2
        ;;
      --expect-final)
        expect_final=1
        shift
        ;;
      --no-expect-final)
        expect_final=0
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for run-now: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$job_ref" ]]; then
    echo "ERROR: --job is required" >&2
    exit 2
  fi
  if ! [[ "$timeout_ms" =~ ^[0-9]+$ ]] || [[ "$timeout_ms" -lt 1000 ]]; then
    timeout_ms=300000
  fi

  job_json="$(resolve_job_json "$job_ref")"
  job_id="$(printf '%s' "$job_json" | jq -r '.id')"
  job_name="$(printf '%s' "$job_json" | jq -r '.name')"

  echo "RUN_NOW job=${job_name} id=${job_id} timeout_ms=${timeout_ms} expect_final=${expect_final}"
  if [[ "$expect_final" -eq 1 ]]; then
    "$OPENCLAW_BIN" cron run "$job_id" --expect-final --timeout "$timeout_ms"
  else
    "$OPENCLAW_BIN" cron run "$job_id" --timeout "$timeout_ms"
  fi
}

command_restart() {
  local job_ref=""
  local timeout_ms="300000"
  local expect_final=0
  local reason="manual_restart"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --job)
        job_ref="${2:-}"
        shift 2
        ;;
      --timeout)
        timeout_ms="${2:-}"
        shift 2
        ;;
      --expect-final)
        expect_final=1
        shift
        ;;
      --reason)
        reason="${2:-manual_restart}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for restart: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$job_ref" ]]; then
    echo "ERROR: --job is required" >&2
    exit 2
  fi
  if ! [[ "$timeout_ms" =~ ^[0-9]+$ ]] || [[ "$timeout_ms" -lt 1000 ]]; then
    timeout_ms=300000
  fi

  command_stop_run --job "$job_ref" --reason "$reason"
  if [[ "$expect_final" -eq 1 ]]; then
    command_run_now --job "$job_ref" --timeout "$timeout_ms" --expect-final
  else
    command_run_now --job "$job_ref" --timeout "$timeout_ms" --no-expect-final
  fi
}

command_stop_run() {
  local job_ref=""
  local keep_disabled=0
  local session_kill=1
  local process_kill=1
  local dry_run=0
  local reason="manual_stop"

  local job_json=""
  local job_id=""
  local job_name=""
  local role=""
  local was_enabled="false"
  local running_at=""
  local session=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --job)
        job_ref="${2:-}"
        shift 2
        ;;
      --keep-disabled)
        keep_disabled=1
        shift
        ;;
      --no-session-kill)
        session_kill=0
        shift
        ;;
      --no-process-kill)
        process_kill=0
        shift
        ;;
      --reason)
        reason="${2:-manual_stop}"
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown option for stop-run: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$job_ref" ]]; then
    echo "ERROR: --job is required" >&2
    exit 2
  fi

  job_json="$(resolve_job_json "$job_ref")"
  job_id="$(printf '%s' "$job_json" | jq -r '.id')"
  job_name="$(printf '%s' "$job_json" | jq -r '.name')"
  was_enabled="$(printf '%s' "$job_json" | jq -r '.enabled')"
  running_at="$(printf '%s' "$job_json" | jq -r '.state.runningAtMs // ""')"
  role="$(role_from_job_json "$job_json")"
  session="$(session_for_role "$role")"

  if [[ "$dry_run" -eq 1 ]]; then
    echo "STOP_RUN_PLAN job=${job_name} id=${job_id} role=${role:-unknown} enabled=${was_enabled} running_at_ms=${running_at:-none} process_kill=${process_kill} session_kill=${session_kill} keep_disabled=${keep_disabled} reason=${reason}"
    exit 0
  fi

  if [[ "$was_enabled" == "true" ]]; then
    "$OPENCLAW_BIN" cron disable "$job_id" >/dev/null 2>&1 || true
  fi

  local proc_killed=0
  local session_killed=0

  if [[ "$process_kill" -eq 1 && -n "$role" ]]; then
    if pkill -f "cron_tmux_role_runner.sh ${role}( |$)" >/dev/null 2>&1; then
      proc_killed=1
    fi
  fi

  if [[ "$session_kill" -eq 1 && -n "$session" ]]; then
    if tmux has-session -t "$session" >/dev/null 2>&1; then
      tmux kill-session -t "$session" >/dev/null 2>&1 || true
      session_killed=1
    fi
  fi

  if [[ "$keep_disabled" -eq 0 && "$was_enabled" == "true" ]]; then
    "$OPENCLAW_BIN" cron enable "$job_id" >/dev/null 2>&1 || true
  fi

  echo "STOP_RUN_RESULT job=${job_name} id=${job_id} role=${role:-unknown} was_enabled=${was_enabled} running_at_ms=${running_at:-none} process_killed=${proc_killed} session_killed=${session_killed} keep_disabled=${keep_disabled} reason=${reason}"
}

command_recover_stale() {
  if [[ ! -x "$STALE_SWEEP_SCRIPT" ]]; then
    echo "ERROR: stale sweep script missing or not executable: $STALE_SWEEP_SCRIPT" >&2
    exit 7
  fi
  bash "$STALE_SWEEP_SCRIPT" "$@"
}

main() {
  local cmd="${1:-help}"
  shift || true

  if ! OPENCLAW_BIN="$(resolve_openclaw_bin)"; then
    echo "ERROR: openclaw binary not found" >&2
    exit 5
  fi
  require_jq
  load_jobs_json

  case "$cmd" in
    status)
      command_status "$@"
      ;;
    pause)
      command_pause "$@"
      ;;
    resume)
      command_resume "$@"
      ;;
    stop-run)
      command_stop_run "$@"
      ;;
    run-now)
      command_run_now "$@"
      ;;
    restart)
      command_restart "$@"
      ;;
    last-summary)
      command_last_summary "$@"
      ;;
    recover-stale)
      command_recover_stale "$@"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      echo "ERROR: unknown command '$cmd'" >&2
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
