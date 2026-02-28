#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

JOB_ID="${ARCHITECT_CRON_JOB_ID:-a80a9f91-75db-4fc9-9258-f61e241e2a38}"
JOB_NAME="${ARCHITECT_CRON_NAME:-architect-tmux-loop}"
STALE_SECONDS="${ARCHITECT_STALE_SECONDS:-120}"
RUN_TIMEOUT_MS="${ARCHITECT_RUN_TIMEOUT_MS:-240000}"
FORCE_RUN_RETRIES="${ARCHITECT_FORCE_RUN_RETRIES:-2}"
AUDIT_LIMIT="${ARCHITECT_AUDIT_LIMIT:-10}"
AUDIT_RECENT_STRICT="${ARCHITECT_AUDIT_RECENT_STRICT:-3}"
SLO_LIMIT="${ARCHITECT_SLO_LIMIT:-30}"
SLO_P95_MAX_MS="${ARCHITECT_SLO_P95_MAX_MS:-180000}"
SLO_TIMEOUT_RATE_MAX="${ARCHITECT_SLO_TIMEOUT_RATE_MAX:-0.20}"
SLO_ERROR_RATE_MAX="${ARCHITECT_SLO_ERROR_RATE_MAX:-0.30}"
ROLE_STATE_DIR="${ARCHITECT_ROLE_STATE_DIR:-/home/venom/.openclaw/cron/role-state}"
LAST_CONTRACT_FILE="${ROLE_STATE_DIR}/architect.last_contract"
GUARD_STREAK_FILE="${ROLE_STATE_DIR}/architect.guard_streak"
GUARD_CONSECUTIVE="${ARCHITECT_GUARD_CONSECUTIVE:-2}"
GUARD_AUTO_RECOVER="${ARCHITECT_GUARD_AUTO_RECOVER:-1}"
TRACE_FILE="${ROOT}/logs-codex-runs/role-runner/architect.live.log"

usage() {
  cat <<'EOF'
Usage: scripts/architect_cron_watch.sh <status|recover|run-once|tail|audit|slo|guard>

Commands:
  status   Print architect cron status + staleness + contract gate summary
  recover  Reset stale running state for architect cron only
  run-once Recover if stale, force-run architect cron, then print latest summary
  tail     Show recent architect role-runner traces
  audit    Audit recent architect runs for contract drift
  slo      Compute rolling SLO (p95 duration + timeout/error rates)
  guard    One-shot health gate (status+audit+slo) with 2-cycle alert hysteresis
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ARCH_WATCH_ERROR missing_command=${cmd}"
    exit 5
  fi
}

now_epoch() {
  date -u +%s
}

normalize_cron_runs_json() {
  local raw="${1:-}"
  if command -v python3 >/dev/null 2>&1 && [[ -f "${ROOT}/scripts/openclaw_cron_runs_normalize.py" ]]; then
    printf '%s' "$raw" | python3 "${ROOT}/scripts/openclaw_cron_runs_normalize.py" 2>/dev/null || echo '{"entries":[]}'
  else
    printf '%s' "$raw"
  fi
}

fetch_runs_json() {
  local limit="${1:-1}"
  local raw=""
  raw="$(openclaw cron runs --id "$JOB_ID" --limit "$limit" 2>/dev/null || echo '{}')"
  normalize_cron_runs_json "$raw"
}

job_json() {
  openclaw cron list --json | jq -c --arg id "$JOB_ID" '.jobs[]? | select(.id==$id)'
}

status_json() {
  local j
  j="$(job_json)"
  if [[ -z "$j" ]]; then
    echo "{}"
    return 0
  fi
  printf '%s' "$j" | jq -c --argjson stale "$STALE_SECONDS" '
    . as $job
    | (if ($job.state.runningAtMs // null) then (((now * 1000) - ($job.state.runningAtMs // 0)) / 1000 | floor) else 0 end) as $running_age
    | {
        id: ($job.id // ""),
        name: ($job.name // ""),
        enabled: ($job.enabled // false),
        last_status: ($job.state.lastStatus // "unknown"),
        running_at_ms: ($job.state.runningAtMs // 0),
        running_age_s: $running_age,
        stale_threshold_s: $stale,
        last_run_ms: ($job.state.lastRunAtMs // 0),
        next_run_ms: ($job.state.nextRunAtMs // 0)
      }'
}

print_contract_gate() {
  if [[ ! -f "$LAST_CONTRACT_FILE" ]]; then
    echo "ARCH_WATCH_CONTRACT status=missing file=${LAST_CONTRACT_FILE}"
    return 0
  fi
  local normalized
  normalized="$(tr '\n' ' ' < "$LAST_CONTRACT_FILE" | tr -s ' ')"
  local missing=()
  local key
  for key in "ARCHITECT_ARTIFACT=" "ARCH_RULE=" "REVIEW_SCOPE=" "CONFORMANCE=" "VIOLATIONS=" "TASK_UPDATE=" "LOCK_CHECK=OK"; do
    if [[ "${normalized^^}" != *"${key}"* ]]; then
      missing+=("${key}")
    fi
  done
  if [[ "${#missing[@]}" -eq 0 ]]; then
    echo "ARCH_WATCH_CONTRACT status=pass file=${LAST_CONTRACT_FILE}"
  else
    echo "ARCH_WATCH_CONTRACT status=warn missing=$(IFS=,; echo "${missing[*]}") file=${LAST_CONTRACT_FILE}"
  fi
}

status_cmd() {
  local j
  j="$(job_json)"
  if [[ -z "$j" ]]; then
    echo "ARCH_WATCH_STATUS status=error reason=job_not_found job_id=${JOB_ID}"
    return 2
  fi
  local now running_ms running_age last_run_ms next_run_ms enabled last_status
  now="$(now_epoch)"
  running_ms="$(printf '%s' "$j" | jq -r '.state.runningAtMs // empty')"
  last_run_ms="$(printf '%s' "$j" | jq -r '.state.lastRunAtMs // empty')"
  next_run_ms="$(printf '%s' "$j" | jq -r '.state.nextRunAtMs // empty')"
  enabled="$(printf '%s' "$j" | jq -r '.enabled')"
  last_status="$(printf '%s' "$j" | jq -r '.state.lastStatus // "unknown"')"
  running_age=0
  if [[ -n "$running_ms" && "$running_ms" =~ ^[0-9]+$ ]]; then
    running_age=$((now - (running_ms / 1000)))
  fi
  echo "ARCH_WATCH_STATUS enabled=${enabled} last_status=${last_status} running_age_s=${running_age} stale_threshold_s=${STALE_SECONDS} last_run_ms=${last_run_ms:-none} next_run_ms=${next_run_ms:-none}"
  print_contract_gate
}

running_age_seconds() {
  local j running_ms now
  j="$(job_json)"
  running_ms="$(printf '%s' "$j" | jq -r '.state.runningAtMs // empty')"
  now="$(now_epoch)"
  if [[ -n "$running_ms" && "$running_ms" =~ ^[0-9]+$ ]]; then
    echo $((now - (running_ms / 1000)))
  else
    echo 0
  fi
}

recover_cmd() {
  STALE_SWEEP_THRESHOLD_SECONDS="${STALE_SECONDS}" bash scripts/stale_cron_sweep.sh --apply --regex "^${JOB_NAME}\$"
}

run_once_cmd() {
  status_cmd || true
  local j running_ms now running_age
  j="$(job_json)"
  running_ms="$(printf '%s' "$j" | jq -r '.state.runningAtMs // empty')"
  now="$(now_epoch)"
  running_age=0
  if [[ -n "$running_ms" && "$running_ms" =~ ^[0-9]+$ ]]; then
    running_age=$((now - (running_ms / 1000)))
  fi
  if [[ "$running_age" -ge "$STALE_SECONDS" ]]; then
    echo "ARCH_WATCH_ACTION stale_detected running_age_s=${running_age} -> recover"
    recover_cmd
  fi

  local attempt=1
  local run_ok=0
  local run_err=""
  while [[ "$attempt" -le "$FORCE_RUN_RETRIES" ]]; do
    if timeout $((RUN_TIMEOUT_MS / 1000))s openclaw cron run "$JOB_ID" --expect-final --timeout "$RUN_TIMEOUT_MS" >/tmp/architect_cron_watch_run.out 2>/tmp/architect_cron_watch_run.err; then
      cat /tmp/architect_cron_watch_run.out
      run_ok=1
      break
    fi
    run_err="$(cat /tmp/architect_cron_watch_run.err 2>/dev/null || true)"
    echo "ARCH_WATCH_WARN force_run_timeout_or_error timeout_ms=${RUN_TIMEOUT_MS} attempt=${attempt}/${FORCE_RUN_RETRIES}"
    if [[ -n "$run_err" ]]; then
      printf '%s\n' "$run_err" | tail -n 3 | sed 's/^/ARCH_WATCH_ERR /'
    fi
    if printf '%s\n' "$run_err" | rg -qi "gateway timeout"; then
      sleep 4
      attempt=$((attempt + 1))
      continue
    fi
    break
  done

  if [[ "$run_ok" -ne 1 ]]; then
    running_age="$(running_age_seconds)"
    if [[ "$running_age" -ge "$STALE_SECONDS" ]]; then
      echo "ARCH_WATCH_ACTION post_timeout_recover running_age_s=${running_age}"
      recover_cmd
    fi
  fi

  fetch_runs_json 1 | jq -r '.entries[0]? | "ARCH_WATCH_LAST_RUN status=\(.status // "unknown") duration_ms=\(.durationMs // 0) run_at_ms=\(.runAtMs // 0)"'
  status_cmd || true
}

tail_cmd() {
  if [[ -f "$TRACE_FILE" ]]; then
    tail -n 60 "$TRACE_FILE"
  else
    echo "ARCH_WATCH_TRACE missing=${TRACE_FILE}"
  fi
}

audit_stats_json() {
  local runs_json
  local tmp_json
  runs_json="$(fetch_runs_json "$AUDIT_LIMIT")"
  tmp_json="$(mktemp)"
  printf '%s' "$runs_json" > "$tmp_json"
  python3 - "$AUDIT_LIMIT" "$AUDIT_RECENT_STRICT" "$tmp_json" <<'PY'
import json
import re
import sys
from pathlib import Path

limit = int(sys.argv[1])
strict_recent = int(sys.argv[2])
obj = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8") or "{}")
entries = obj.get("entries", []) or []

required = (
    "ARCHITECT_ARTIFACT=",
    "ARCH_RULE=",
    "REVIEW_SCOPE=",
    "CONFORMANCE=",
    "VIOLATIONS=",
    "TASK_UPDATE=",
    "LOCK_CHECK=OK",
)
invalid_updates = {"CLAIM", "COMPLETE", "HANDOFF"}
summary_total = 0
missing_contract = 0
invalid_task_update = 0
conformance_pass = 0
conformance_warn = 0
conformance_blocked = 0
errors = 0
recent_entries_checked = 0
recent_errors = 0
recent_summaries_checked = 0
recent_missing_contract = 0
recent_invalid_task_update = 0

for e in entries:
    status = str(e.get("status") or "").strip().lower()
    is_recent_entry = recent_entries_checked < strict_recent
    if is_recent_entry:
        recent_entries_checked += 1
        if status == "error":
            recent_errors += 1
    if status == "error":
        errors += 1
    summary = str(e.get("summary") or "")
    if not summary:
        continue
    summary_total += 1
    is_recent_summary = recent_summaries_checked < strict_recent
    if is_recent_summary:
        recent_summaries_checked += 1
    up = summary.upper()
    if not all(tok in up for tok in required):
        missing_contract += 1
        if is_recent_summary:
            recent_missing_contract += 1
    m_update = re.search(r"TASK_UPDATE=([A-Z_]+)", up)
    if m_update and m_update.group(1) in invalid_updates:
        invalid_task_update += 1
        if is_recent_summary:
            recent_invalid_task_update += 1
    m_conf = re.search(r"CONFORMANCE=([A-Z_]+)", up)
    if m_conf:
        conf = m_conf.group(1)
        if conf == "PASS":
            conformance_pass += 1
        elif conf == "WARN":
            conformance_warn += 1
        elif conf == "BLOCKED":
            conformance_blocked += 1

stats = {
    "limit": limit,
    "entries": len(entries),
    "summaries": summary_total,
    "errors": errors,
    "missing_contract": missing_contract,
    "invalid_task_update": invalid_task_update,
    "recent_entries": recent_entries_checked,
    "recent_errors": recent_errors,
    "recent_summaries": recent_summaries_checked,
    "recent_missing_contract": recent_missing_contract,
    "recent_invalid_task_update": recent_invalid_task_update,
    "conformance_pass": conformance_pass,
    "conformance_warn": conformance_warn,
    "conformance_blocked": conformance_blocked,
}
print(json.dumps(stats, separators=(",", ":")))
PY
  rm -f "$tmp_json"
}

print_audit_line() {
  jq -r '"ARCH_WATCH_AUDIT limit=\(.limit) entries=\(.entries) summaries=\(.summaries) errors=\(.errors) missing_contract=\(.missing_contract) invalid_task_update=\(.invalid_task_update) recent_entries=\(.recent_entries) recent_errors=\(.recent_errors) recent_summaries=\(.recent_summaries) recent_missing_contract=\(.recent_missing_contract) recent_invalid_task_update=\(.recent_invalid_task_update) conformance_pass=\(.conformance_pass) conformance_warn=\(.conformance_warn) conformance_blocked=\(.conformance_blocked)"'
}

audit_cmd() {
  local stats
  stats="$(audit_stats_json)"
  print_audit_line <<<"$stats"
  if jq -e '.recent_missing_contract > 0 or .recent_invalid_task_update > 0' >/dev/null <<<"$stats"; then
    return 2
  fi
}

slo_stats_json() {
  local runs_json
  local tmp_json
  runs_json="$(fetch_runs_json "$SLO_LIMIT")"
  tmp_json="$(mktemp)"
  printf '%s' "$runs_json" > "$tmp_json"
  python3 - "$SLO_LIMIT" "$SLO_P95_MAX_MS" "$SLO_TIMEOUT_RATE_MAX" "$SLO_ERROR_RATE_MAX" "$tmp_json" <<'PY'
import json
import math
import sys
from pathlib import Path

limit = int(sys.argv[1])
p95_max_ms = int(float(sys.argv[2]))
timeout_rate_max = float(sys.argv[3])
error_rate_max = float(sys.argv[4])
obj = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8") or "{}")
entries = obj.get("entries", []) or []

durations = []
errors = 0
timeouts = 0
for e in entries:
    duration = e.get("durationMs")
    if isinstance(duration, int) and duration >= 0:
        durations.append(duration)
    status = str(e.get("status") or "").strip().lower()
    if status == "error":
        errors += 1
        err = str(e.get("error") or "").lower()
        if "timed out" in err or "timeout" in err:
            timeouts += 1

durations.sort()
n = len(durations)
if n == 0:
    p95 = 0
else:
    idx = max(0, min(n - 1, math.ceil(0.95 * n) - 1))
    p95 = durations[idx]

entry_count = len(entries)
timeout_rate = (timeouts / entry_count) if entry_count else 0.0
error_rate = (errors / entry_count) if entry_count else 0.0

gate = "pass"
reasons = []
if entry_count > 0 and p95 > p95_max_ms:
    gate = "warn"
    reasons.append("p95_gt_budget")
if entry_count > 0 and timeout_rate > timeout_rate_max:
    gate = "warn"
    reasons.append("timeout_rate_gt_budget")
if entry_count > 0 and error_rate > error_rate_max:
    gate = "warn"
    reasons.append("error_rate_gt_budget")

stats = {
    "limit": limit,
    "entries": entry_count,
    "duration_samples": n,
    "p95_duration_ms": p95,
    "error_count": errors,
    "timeout_count": timeouts,
    "error_rate": round(error_rate, 4),
    "timeout_rate": round(timeout_rate, 4),
    "gate": gate,
    "reasons": reasons,
    "thresholds": {
        "p95_max_ms": p95_max_ms,
        "timeout_rate_max": timeout_rate_max,
        "error_rate_max": error_rate_max,
    },
}
print(json.dumps(stats, separators=(",", ":")))
PY
  rm -f "$tmp_json"
}

print_slo_line() {
  jq -r '"ARCH_WATCH_SLO limit=\(.limit) entries=\(.entries) duration_samples=\(.duration_samples) p95_duration_ms=\(.p95_duration_ms) error_count=\(.error_count) timeout_count=\(.timeout_count) error_rate=\(.error_rate) timeout_rate=\(.timeout_rate) gate=\(.gate) reasons=\((.reasons | if length == 0 then "none" else join(",") end)) thresholds_p95_ms=\(.thresholds.p95_max_ms) thresholds_timeout_rate=\(.thresholds.timeout_rate_max) thresholds_error_rate=\(.thresholds.error_rate_max)"'
}

slo_cmd() {
  local stats
  stats="$(slo_stats_json)"
  print_slo_line <<<"$stats"
}

read_guard_streak() {
  if [[ ! -f "$GUARD_STREAK_FILE" ]]; then
    echo 0
    return 0
  fi
  local raw
  raw="$(tr -cd '0-9' < "$GUARD_STREAK_FILE" || true)"
  if [[ -z "$raw" ]]; then
    echo 0
  else
    echo "$raw"
  fi
}

write_guard_streak() {
  local value="${1:-0}"
  mkdir -p "$ROLE_STATE_DIR"
  printf '%s\n' "$value" > "$GUARD_STREAK_FILE"
}

guard_cmd() {
  local sjson ajson slojson
  sjson="$(status_json)"
  if [[ "$sjson" == "{}" ]]; then
    echo "ARCH_WATCH_GUARD state=alert reason=job_not_found job_id=${JOB_ID}"
    return 2
  fi
  ajson="$(audit_stats_json)"
  slojson="$(slo_stats_json)"

  local running_age running_at_ms last_status enabled
  local recent_missing recent_invalid
  local drift=0 prev_streak=0 streak=0
  local state="ok" reasons="" recover_action="none"
  enabled="$(jq -r '.enabled' <<<"$sjson")"
  last_status="$(jq -r '.last_status' <<<"$sjson")"
  running_age="$(jq -r '.running_age_s' <<<"$sjson")"
  running_at_ms="$(jq -r '.running_at_ms' <<<"$sjson")"
  recent_missing="$(jq -r '.recent_missing_contract' <<<"$ajson")"
  recent_invalid="$(jq -r '.recent_invalid_task_update' <<<"$ajson")"

  if [[ "${recent_missing}" -gt 0 || "${recent_invalid}" -gt 0 ]]; then
    drift=1
  fi

  prev_streak="$(read_guard_streak)"
  if [[ "$drift" -eq 1 ]]; then
    streak=$((prev_streak + 1))
  else
    streak=0
  fi
  write_guard_streak "$streak"

  if [[ "$GUARD_AUTO_RECOVER" == "1" && "$running_at_ms" =~ ^[0-9]+$ && "$running_at_ms" -gt 0 && "$running_age" -ge "$STALE_SECONDS" ]]; then
    if recover_cmd >/tmp/architect_guard_recover.out 2>/tmp/architect_guard_recover.err; then
      recover_action="applied"
    else
      recover_action="failed"
    fi
  fi

  if [[ "$enabled" != "true" ]]; then
    state="alert"
    reasons="job_disabled"
  elif [[ "$last_status" == "error" ]]; then
    state="warming"
    reasons="last_status_error"
  fi

  if [[ "$drift" -eq 1 ]]; then
    if [[ "$streak" -ge "$GUARD_CONSECUTIVE" ]]; then
      state="alert"
      reasons="${reasons:+${reasons},}contract_drift_consecutive"
    else
      if [[ "$state" != "alert" ]]; then
        state="warming"
      fi
      reasons="${reasons:+${reasons},}contract_drift_warming"
    fi
  fi

  if [[ "$(jq -r '.gate' <<<"$slojson")" != "pass" ]]; then
    if [[ "$state" == "ok" ]]; then
      state="warming"
    fi
    reasons="${reasons:+${reasons},}slo_warn"
  fi

  if [[ -z "$reasons" ]]; then
    reasons="none"
  fi

  echo "ARCH_WATCH_GUARD state=${state} enabled=${enabled} last_status=${last_status} running_age_s=${running_age} contract_drift=${drift} drift_streak=${streak} drift_threshold=${GUARD_CONSECUTIVE} recover_action=${recover_action} reasons=${reasons}"
  print_audit_line <<<"$ajson"
  print_slo_line <<<"$slojson"

  if [[ "$state" == "alert" ]]; then
    return 2
  fi
}

main() {
  require_cmd openclaw
  require_cmd jq
  local cmd="${1:-status}"
  case "$cmd" in
    status) status_cmd ;;
    recover) recover_cmd ;;
    run-once) run_once_cmd ;;
    tail) tail_cmd ;;
    audit) audit_cmd ;;
    slo) slo_cmd ;;
    guard) guard_cmd ;;
    -h|--help|help) usage ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
