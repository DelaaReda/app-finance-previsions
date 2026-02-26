#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

ROLE_MAP=(
  "planner:09d045db-b12a-4486-a743-57b761d52e50"
  "dev:dfd61f17-206f-4feb-ab14-6ae4ce54f04c"
  "tester:36bed423-e965-4a19-a43a-c8ffbff751d8"
  "qa:454dc361-14bb-4f71-8ca2-ec86708c503f"
  "architect:bde5885a-388f-4fe4-a8b7-a146521d9e9d"
  "po:44f08bd9-b9c0-4ab5-8882-cc91d402c8db"
  "scrum_master:8e5b1bd7-f319-48d8-b8f7-c906c024135f"
  "clawsentinel:25756cb4-57f1-41c7-83d4-66fd67a0164d"
)

STOP_ON_FAILURE=1
TIMEOUT_SECONDS="${SEQUENTIAL_VALIDATE_TIMEOUT_SECONDS:-300000}"
ROLE_FILTER=""
REPORT_DIR="${SEQUENTIAL_VALIDATE_REPORT_DIR:-$ROOT/logs-codex-runs/role-runner}"
REPORT_FILE=""
STRICT_READY_CHAIN=0
CHAIN_TARGET="${SEQUENTIAL_VALIDATE_CHAIN_TARGET:-}"
PRINT_SUMMARY=1

usage() {
  cat <<'EOF'
Usage: validate_roles_sequential.sh [options]

Run one role at a time and enforce role-delivery health gates.

Options:
  --roles <csv>              Roles subset (example: planner,dev,qa)
  --timeout-ms <n>           Timeout for `openclaw cron run` (default: 300000)
  --report-file <path>       JSONL report path (default: auto timestamped file)
  --strict-ready-chain       Enforce handoff on a single BATCH target (planner->dev->tester->qa)
  --chain-target <BATCH-ID>  Predefine expected BATCH target (example: BATCH-02)
  --no-summary               Disable end-of-run report summary
  --continue-on-failure      Continue sweep even if one role fails gates
  --stop-on-failure          Stop at first failing role (default)
  -h, --help                 Show this help
EOF
}

extract_field() {
  local key="$1"
  local summary="$2"
  printf '%s\n' "$summary" \
    | sed -n "s/^${key}:[[:space:]]*//p" \
    | head -n 1 \
    | tr -d '\r' \
    | sed 's/[[:space:]]*$//'
}

artifact_marker_for_role() {
  case "$1" in
    planner) echo "PLANNER_ARTIFACT=" ;;
    dev) echo "DEV_ARTIFACT=" ;;
    tester) echo "TESTER_ARTIFACT=" ;;
    qa) echo "QA_ARTIFACT=" ;;
    architect) echo "ARCHITECT_ARTIFACT=" ;;
    po) echo "PO_ARTIFACT=" ;;
    scrum_master) echo "SCRUM_ARTIFACT=" ;;
    clawsentinel) echo "SENTINEL_ARTIFACT=" ;;
    *) echo "ROLE_ARTIFACT=" ;;
  esac
}

blocker_is_clear() {
  local blocker_u
  blocker_u="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
  [[ -z "$blocker_u" || "$blocker_u" == "NONE" || "$blocker_u" == "AUCUN" ]]
}

is_chain_core_role() {
  case "$1" in
    planner|dev|tester|qa) return 0 ;;
    *) return 1 ;;
  esac
}

extract_batch_target() {
  local text="$*"
  printf '%s\n' "$text" \
    | tr '[:lower:]' '[:upper:]' \
    | grep -oE 'BATCH-[0-9]+' \
    | head -n 1 || true
}

ready_batch_ids_csv() {
  if [[ ! -f "docs/orchestrator-ops/priority-queue.json" ]]; then
    echo ""
    return 0
  fi
  jq -r '[.items[]? | select((.state // "")=="READY") | (.id // "")] | map(select(length>0)) | join(",")' \
    docs/orchestrator-ops/priority-queue.json 2>/dev/null || echo ""
}

batch_target_is_ready() {
  local target="$1"
  if [[ -z "$target" || ! -f "docs/orchestrator-ops/priority-queue.json" ]]; then
    return 1
  fi
  jq -e --arg id "$target" '.items[]? | select(.id==$id and (.state // "")=="READY")' \
    docs/orchestrator-ops/priority-queue.json >/dev/null 2>&1
}

role_requires_exec_evidence() {
  case "$1" in
    dev|tester|qa) return 0 ;;
    *) return 1 ;;
  esac
}

disable_all_role_jobs() {
  local pair=""
  local id=""
  for pair in "${ROLE_MAP[@]}"; do
    id="${pair#*:}"
    openclaw cron disable "$id" >/dev/null 2>&1 || true
  done
}

count_role_jobs_present() {
  local cron_json=""
  local pair=""
  local id=""
  local count=0
  cron_json="$(openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}' )"
  for pair in "${ROLE_MAP[@]}"; do
    id="${pair#*:}"
    if printf '%s' "$cron_json" | jq -e --arg id "$id" '.jobs[]? | select(.id==$id)' >/dev/null 2>&1; then
      count=$((count + 1))
    fi
  done
  printf '%s\n' "$count"
}

append_jsonl_event() {
  local role="$1"
  local status="$2"
  local delta="$3"
  local verdict="$4"
  local blocker="$5"
  local next_action="$6"
  local duration_ms="$7"
  local tokens="$8"
  local artifact_marker="$9"
  local artifact_present="${10}"
  local gate_ok="${11}"
  local failure_reason="${12}"
  local evidence_head="${13}"
  local strict_ready_chain="${14}"
  local chain_target_expected="${15}"
  local chain_target_observed="${16}"
  local chain_check_ok="${17}"
  local now_iso
  now_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  jq -nc \
    --arg ts "$now_iso" \
    --arg role "$role" \
    --arg status "$status" \
    --arg delta "$delta" \
    --arg verdict "$verdict" \
    --arg blocker "$blocker" \
    --arg next_action "$next_action" \
    --arg duration_ms "$duration_ms" \
    --arg tokens "$tokens" \
    --arg artifact_marker "$artifact_marker" \
    --argjson artifact_present "$artifact_present" \
    --argjson gate_ok "$gate_ok" \
    --arg failure_reason "$failure_reason" \
    --arg evidence_head "$evidence_head" \
    --argjson strict_ready_chain "$strict_ready_chain" \
    --arg chain_target_expected "$chain_target_expected" \
    --arg chain_target_observed "$chain_target_observed" \
    --argjson chain_check_ok "$chain_check_ok" \
    '{ts:$ts,role:$role,status:$status,delta:$delta,verdict:$verdict,blocker_id:$blocker,next_action_unique:$next_action,duration_ms:($duration_ms|tonumber?),tokens_total:($tokens|tonumber?),artifact_marker:$artifact_marker,artifact_present:$artifact_present,gate_ok:$gate_ok,failure_reason:$failure_reason,evidence_head:$evidence_head,strict_ready_chain:$strict_ready_chain,chain_target_expected:$chain_target_expected,chain_target_observed:$chain_target_observed,chain_check_ok:$chain_check_ok}' \
    >> "$REPORT_FILE"
}

print_report_summary() {
  local report_file="$1"
  local summary_json=""
  local total=""
  local gate_ok=""
  local failed=""
  local avg_duration=""
  local avg_tokens=""

  if [[ ! -s "$report_file" ]]; then
    echo "SEQUENTIAL_SUMMARY total=0 gate_ok=0 failed=0 avg_duration_ms=0 avg_tokens=0 report=$report_file"
    return 0
  fi

  summary_json="$(jq -cs '{
    total: length,
    gate_ok: ([.[] | select(.gate_ok==true)] | length),
    failed: ([.[] | select(.gate_ok!=true)] | length),
    avg_duration_ms: (([.[].duration_ms // 0] | add) / length),
    avg_tokens: (([.[].tokens_total // 0] | add) / length)
  }' "$report_file")"

  total="$(jq -r '.total' <<<"$summary_json")"
  gate_ok="$(jq -r '.gate_ok' <<<"$summary_json")"
  failed="$(jq -r '.failed' <<<"$summary_json")"
  avg_duration="$(jq -r '.avg_duration_ms' <<<"$summary_json" | awk '{printf "%.2f",$1}')"
  avg_tokens="$(jq -r '.avg_tokens' <<<"$summary_json" | awk '{printf "%.2f",$1}')"

  echo "SEQUENTIAL_SUMMARY total=${total} gate_ok=${gate_ok} failed=${failed} avg_duration_ms=${avg_duration} avg_tokens=${avg_tokens} report=${report_file}"
  jq -rs '
    sort_by(.role)
    | group_by(.role)
    | map({
        role: .[0].role,
        total: length,
        ok: ([.[] | select(.gate_ok==true)] | length),
        failed: ([.[] | select(.gate_ok!=true)] | length),
        avg_duration_ms: (([.[].duration_ms // 0] | add) / length),
        avg_tokens: (([.[].tokens_total // 0] | add) / length),
        latest_failure: (.[-1].failure_reason // "NONE"),
        latest_next: (.[-1].next_action_unique // "n/a"),
        latest_chain_expected: (.[-1].chain_target_expected // ""),
        latest_chain_observed: (.[-1].chain_target_observed // "")
      })
    | .[]
    | "ROLE_SUMMARY role=\(.role) total=\(.total) ok=\(.ok) failed=\(.failed) avg_duration_ms=\(.avg_duration_ms) avg_tokens=\(.avg_tokens) latest_failure=\(.latest_failure) chain_expected=\(.latest_chain_expected) chain_observed=\(.latest_chain_observed) latest_next=\(.latest_next)"
  ' "$report_file"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --roles)
      ROLE_FILTER="${2:-}"
      shift 2
      ;;
    --timeout-ms)
      TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --report-file)
      REPORT_FILE="${2:-}"
      shift 2
      ;;
    --strict-ready-chain)
      STRICT_READY_CHAIN=1
      shift
      ;;
    --chain-target)
      CHAIN_TARGET="${2:-}"
      shift 2
      ;;
    --no-summary)
      PRINT_SUMMARY=0
      shift
      ;;
    --continue-on-failure)
      STOP_ON_FAILURE=0
      shift
      ;;
    --stop-on-failure)
      STOP_ON_FAILURE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TIMEOUT_SECONDS" -lt 1000 ]]; then
  echo "Invalid --timeout-ms: $TIMEOUT_SECONDS" >&2
  exit 2
fi

if [[ -n "$CHAIN_TARGET" ]]; then
  CHAIN_TARGET="$(printf '%s' "$CHAIN_TARGET" | tr '[:lower:]' '[:upper:]')"
  if ! [[ "$CHAIN_TARGET" =~ ^BATCH-[0-9]+$ ]]; then
    echo "Invalid --chain-target: $CHAIN_TARGET (expected BATCH-<n>)" >&2
    exit 2
  fi
  STRICT_READY_CHAIN=1
fi

mkdir -p "$REPORT_DIR"
if [[ -z "$REPORT_FILE" ]]; then
  REPORT_FILE="$REPORT_DIR/sequential-validate-$(date -u +%Y%m%dT%H%M%SZ).jsonl"
fi

declare -A ROLE_FILTER_MAP=()
if [[ -n "$ROLE_FILTER" ]]; then
  while IFS= read -r role; do
    [[ -z "$role" ]] && continue
    ROLE_FILTER_MAP["$role"]=1
  done < <(printf '%s\n' "$ROLE_FILTER" | tr ',; ' '\n' | sed '/^$/d')
fi

if [[ "$STRICT_READY_CHAIN" -eq 1 && -z "$CHAIN_TARGET" && "${#ROLE_FILTER_MAP[@]}" -gt 0 ]]; then
  has_planner=0
  has_core_without_planner=0
  for check_role in "${!ROLE_FILTER_MAP[@]}"; do
    if [[ "$check_role" == "planner" ]]; then
      has_planner=1
    elif is_chain_core_role "$check_role"; then
      has_core_without_planner=1
    fi
  done
  if [[ "$has_planner" -eq 0 && "$has_core_without_planner" -eq 1 ]]; then
    echo "strict-ready-chain requires planner in --roles or explicit --chain-target BATCH-<n>" >&2
    exit 2
  fi
fi

trap 'disable_all_role_jobs' EXIT
role_jobs_present="$(count_role_jobs_present)"
if [[ ! "$role_jobs_present" =~ ^[0-9]+$ ]]; then
  role_jobs_present=0
fi
if [[ "$role_jobs_present" -eq 0 ]]; then
  echo "SEQUENTIAL_ROLE_VALIDATION_ABORT reason=NO_ROLE_CRON_JOBS_CONFIGURED" >&2
  echo "Hint: reconfigure role jobs first (scripts/configure_tmux_role_crons.sh)." >&2
  exit 11
fi
disable_all_role_jobs

echo "SEQUENTIAL_ROLE_VALIDATION_START"
echo "REPORT_FILE=$REPORT_FILE"

for pair in "${ROLE_MAP[@]}"; do
  role="${pair%%:*}"
  id="${pair#*:}"
  out_json="/tmp/role_${role}_latest.json"

  if [[ "${#ROLE_FILTER_MAP[@]}" -gt 0 ]] && [[ -z "${ROLE_FILTER_MAP[$role]:-}" ]]; then
    continue
  fi

  echo "--- ROLE ${role} ENABLE ---"
  openclaw cron enable "$id" >/dev/null
  openclaw cron run "$id" --expect-final --timeout "$TIMEOUT_SECONDS" >/dev/null
  openclaw cron runs --id "$id" --limit 1 > "$out_json"

  summary="$(jq -r '.entries[0].summary // ""' "$out_json")"
  duration="$(jq -r '.entries[0].durationMs // ""' "$out_json")"
  tokens="$(jq -r '.entries[0].usage.total_tokens // ""' "$out_json")"

  status="$(extract_field "STATUS" "$summary")"
  delta="$(extract_field "DELTA" "$summary")"
  verdict="$(extract_field "VERDICT" "$summary")"
  blocker="$(extract_field "BLOCKER_ID" "$summary")"
  next_action="$(extract_field "NEXT_ACTION_UNIQUE" "$summary")"
  evidence_full="$(extract_field "EVIDENCE" "$summary")"
  evidence_head="$(printf '%s' "$evidence_full" | tr '\n' ' ' | tr -s ' ' | cut -c1-180)"
  ready_ids_csv="$(ready_batch_ids_csv)"
  queue_has_ready_rt=false
  if [[ -n "$ready_ids_csv" ]]; then
    queue_has_ready_rt=true
  fi

  marker="$(artifact_marker_for_role "$role")"
  marker_u="$(printf '%s' "$marker" | tr '[:lower:]' '[:upper:]')"
  evidence_u="$(printf '%s' "$evidence_full" | tr '[:lower:]' '[:upper:]')"
  evidence_l="$(printf '%s' "$evidence_full" | tr '[:upper:]' '[:lower:]')"
  chain_observed="$(extract_batch_target "$next_action $delta $evidence_full")"
  chain_check_ok=true
  artifact_present=false
  gate_ok=true
  failure_reason="NONE"

  if [[ "$evidence_u" == *"$marker_u"* ]]; then
    artifact_present=true
  fi

  status_u="$(printf '%s' "$status" | tr '[:lower:]' '[:upper:]')"
  verdict_u="$(printf '%s' "$verdict" | tr '[:lower:]' '[:upper:]')"
  blocker_u="$(printf '%s' "$blocker" | tr '[:lower:]' '[:upper:]')"

  if [[ "$artifact_present" != "true" ]]; then
    gate_ok=false
    if [[ "$failure_reason" == "NONE" ]]; then
      failure_reason="ARTIFACT_MISSING"
    else
      failure_reason="${failure_reason},ARTIFACT_MISSING"
    fi
  fi
  if [[ "$status_u" == "BLOCKED" || "$verdict_u" == "BLOCKED" ]]; then
    gate_ok=false
    if [[ "$failure_reason" == "NONE" ]]; then
      failure_reason="STATUS_OR_VERDICT_BLOCKED"
    else
      failure_reason="${failure_reason},STATUS_OR_VERDICT_BLOCKED"
    fi
  fi
  if [[ "$blocker_u" == "ROLE_CONTRACT_MISSING" ]]; then
    gate_ok=false
    if [[ "$failure_reason" == "NONE" ]]; then
      failure_reason="ROLE_CONTRACT_MISSING"
    else
      failure_reason="${failure_reason},ROLE_CONTRACT_MISSING"
    fi
  fi
  if ! blocker_is_clear "$blocker"; then
    gate_ok=false
    if [[ "$failure_reason" == "NONE" ]]; then
      failure_reason="BLOCKER_NOT_CLEAR"
    else
      failure_reason="${failure_reason},BLOCKER_NOT_CLEAR"
    fi
  fi

  if role_requires_exec_evidence "$role" && [[ "$queue_has_ready_rt" == "true" ]]; then
    if [[ "$evidence_l" != *"cmd="* ]]; then
      gate_ok=false
      if [[ "$failure_reason" == "NONE" ]]; then
        failure_reason="EXEC_CMD_EVIDENCE_MISSING"
      else
        failure_reason="${failure_reason},EXEC_CMD_EVIDENCE_MISSING"
      fi
    fi
  fi
  if [[ "$role" == "tester" && "$queue_has_ready_rt" == "true" ]]; then
    if [[ "$evidence_l" != *"test_result="* ]]; then
      gate_ok=false
      if [[ "$failure_reason" == "NONE" ]]; then
        failure_reason="TEST_RESULT_EVIDENCE_MISSING"
      else
        failure_reason="${failure_reason},TEST_RESULT_EVIDENCE_MISSING"
      fi
    fi
  fi

  if [[ "$STRICT_READY_CHAIN" -eq 1 ]] && is_chain_core_role "$role"; then
    if [[ "$role" == "planner" ]]; then
      if [[ "$queue_has_ready_rt" != "true" ]]; then
        gate_ok=false
        chain_check_ok=false
        if [[ "$failure_reason" == "NONE" ]]; then
          failure_reason="QUEUE_HAS_NO_READY_ITEMS"
        else
          failure_reason="${failure_reason},QUEUE_HAS_NO_READY_ITEMS"
        fi
      fi
      if [[ -z "$chain_observed" ]]; then
        gate_ok=false
        chain_check_ok=false
        if [[ "$failure_reason" == "NONE" ]]; then
          failure_reason="CHAIN_TARGET_MISSING_ON_PLANNER"
        else
          failure_reason="${failure_reason},CHAIN_TARGET_MISSING_ON_PLANNER"
        fi
      else
        if [[ -n "$CHAIN_TARGET" && "$chain_observed" != "$CHAIN_TARGET" ]]; then
          gate_ok=false
          chain_check_ok=false
          if [[ "$failure_reason" == "NONE" ]]; then
            failure_reason="CHAIN_TARGET_MISMATCH_ON_PLANNER"
          else
            failure_reason="${failure_reason},CHAIN_TARGET_MISMATCH_ON_PLANNER"
          fi
        fi
        if [[ -n "$chain_observed" ]] && ! batch_target_is_ready "$chain_observed"; then
          gate_ok=false
          chain_check_ok=false
          if [[ "$failure_reason" == "NONE" ]]; then
            failure_reason="CHAIN_TARGET_NOT_READY_RUNTIME"
          else
            failure_reason="${failure_reason},CHAIN_TARGET_NOT_READY_RUNTIME"
          fi
        fi
        if [[ -z "$CHAIN_TARGET" ]]; then
          CHAIN_TARGET="$chain_observed"
        fi
      fi
    else
      if [[ -z "$CHAIN_TARGET" ]]; then
        gate_ok=false
        chain_check_ok=false
        if [[ "$failure_reason" == "NONE" ]]; then
          failure_reason="CHAIN_TARGET_UNSET"
        else
          failure_reason="${failure_reason},CHAIN_TARGET_UNSET"
        fi
      elif [[ -z "$chain_observed" ]]; then
        gate_ok=false
        chain_check_ok=false
        if [[ "$failure_reason" == "NONE" ]]; then
          failure_reason="CHAIN_TARGET_MISSING_ON_ROLE"
        else
          failure_reason="${failure_reason},CHAIN_TARGET_MISSING_ON_ROLE"
        fi
      elif [[ "$chain_observed" != "$CHAIN_TARGET" ]]; then
        gate_ok=false
        chain_check_ok=false
        if [[ "$failure_reason" == "NONE" ]]; then
          failure_reason="CHAIN_TARGET_MISMATCH_ON_ROLE"
        else
          failure_reason="${failure_reason},CHAIN_TARGET_MISMATCH_ON_ROLE"
        fi
      elif ! batch_target_is_ready "$chain_observed"; then
        gate_ok=false
        chain_check_ok=false
        if [[ "$failure_reason" == "NONE" ]]; then
          failure_reason="CHAIN_TARGET_NOT_READY_RUNTIME"
        else
          failure_reason="${failure_reason},CHAIN_TARGET_NOT_READY_RUNTIME"
        fi
      fi
    fi
  fi

  echo "ROLE=${role} STATUS=${status:-n/a} DELTA=${delta:-n/a} VERDICT=${verdict:-n/a} BLOCKER=${blocker:-n/a} DURATION_MS=${duration:-n/a} TOKENS=${tokens:-n/a} GATE_OK=${gate_ok}"
  echo "ROLE=${role} NEXT_ACTION=${next_action:-n/a}"
  echo "ROLE=${role} CHAIN_EXPECTED=${CHAIN_TARGET:-n/a} CHAIN_OBSERVED=${chain_observed:-n/a} CHAIN_OK=${chain_check_ok} READY_IDS=${ready_ids_csv:-none}"
  echo "ROLE=${role} EVIDENCE_HEAD=${evidence_head:-n/a}"

  append_jsonl_event \
    "$role" "$status" "$delta" "$verdict" "$blocker" "$next_action" \
    "$duration" "$tokens" "$marker" "$artifact_present" "$gate_ok" "$failure_reason" "$evidence_head" \
    "$([[ "$STRICT_READY_CHAIN" -eq 1 ]] && echo true || echo false)" "$CHAIN_TARGET" "${chain_observed:-}" "$chain_check_ok"

  openclaw cron disable "$id" >/dev/null
  echo "--- ROLE ${role} DISABLE ---"

  if [[ "$gate_ok" != "true" && "$STOP_ON_FAILURE" -eq 1 ]]; then
    echo "SEQUENTIAL_ROLE_VALIDATION_ABORT role=${role} reason=${failure_reason}" >&2
    echo "SEQUENTIAL_ROLE_VALIDATION_DONE_WITH_FAILURES"
    if [[ "$PRINT_SUMMARY" -eq 1 ]]; then
      print_report_summary "$REPORT_FILE"
    fi
    openclaw cron list
    exit 10
  fi
done

echo "SEQUENTIAL_ROLE_VALIDATION_DONE"
if [[ "$PRINT_SUMMARY" -eq 1 ]]; then
  print_report_summary "$REPORT_FILE"
fi
openclaw cron list
