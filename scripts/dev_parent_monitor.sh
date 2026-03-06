#!/usr/bin/env bash
# dev_parent_monitor.sh — quality monitor for dev role autonomy/delivery evidence
# Usage:
#   bash scripts/dev_parent_monitor.sh
#   bash scripts/dev_parent_monitor.sh --strict
#   bash scripts/dev_parent_monitor.sh --strict --append-memory
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

STRICT=0
APPEND_MEMORY=0
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --append-memory) APPEND_MEMORY=1 ;;
  esac
done

STATE_DIR_DEFAULT="/home/venom/.openclaw/cron/role-state"
STATE_DIR_ALT="${HOME}/.openclaw/cron/role-state"
STATE_DIR_OVERRIDE="${DEV_PARENT_STATE_DIR:-}"
if [[ -n "$STATE_DIR_OVERRIDE" ]]; then
  STATE_DIR="$STATE_DIR_OVERRIDE"
elif [[ -d "$STATE_DIR_DEFAULT" ]]; then
  STATE_DIR="$STATE_DIR_DEFAULT"
else
  STATE_DIR="$STATE_DIR_ALT"
fi

CONTRACT_FILE="$STATE_DIR/dev.last_contract"
TICK_LOG="$ROOT/logs-codex-runs/fc-ticks/dev.tick.log"
EVENTS_FILE="${DEV_PARENT_EVENTS_FILE:-$ROOT/logs-codex-runs/executor-monitoring/events.jsonl}"
MEMORY_FILE="$ROOT/memory/agents/dev.md"
JSON_OUT="${ROOT}/logs-codex-runs/dev-parent/latest.json"
ESCALATION_OUT="${STATE_DIR}/dev.parent.escalation.json"

if [[ ! -f "$CONTRACT_FILE" ]]; then
  mkdir -p "$(dirname "$JSON_OUT")"
  python3 - "$JSON_OUT" "$CONTRACT_FILE" <<'PY' >/dev/null 2>&1 || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
payload = {
    "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "status": "BLOCKED",
    "verdict": "WARN",
    "task_update": "none_no_signal",
    "next_action_unique": "WAIT_DEV_CONTRACT_FILE",
    "failures_last_24h": 0,
    "contract_markers": 0,
    "action_markers": 0,
    "run_note_words": 0,
    "quality_score": 0,
    "quality": "WEAK",
    "missing_fields": ["contract_file"],
    "invalid_fields": [],
    "channels_missing_streak_24h": 0,
    "none_signal_streak_24h": 0,
    "contract_guard_block_count_24h": 0,
    "issue_reporting_ok_rate_24h": 0,
    "issue_reporting_total_24h": 0,
    "issue_reporting_ok_count_24h": 0,
    "coaching_state": "STALLED",
    "reason": "missing_contract_file",
    "contract_file": sys.argv[2],
}
out.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
  echo "DEV_PARENT: BLOCKED"
  echo "reason=missing_contract_file"
  echo "contract_file=$CONTRACT_FILE"
  echo "json_out=${JSON_OUT}"
  if [[ "$STRICT" -eq 1 ]]; then
    exit 1
  fi
  echo "strict_verdict=WARN"
  exit 0
fi

evidence_line="$(sed -n 's/^EVIDENCE:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"
task_update="$(printf '%s\n' "$evidence_line" | tr ';' '\n' | sed -n 's/^[[:space:]]*task_update=//p' | head -1)"
status="$(sed -n 's/^STATUS:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"
verdict="$(sed -n 's/^VERDICT:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"
next_action="$(sed -n 's/^NEXT_ACTION_UNIQUE:[[:space:]]*//p' "$CONTRACT_FILE" | head -1)"

ev_get() {
  local key="$1"
  printf '%s\n' "$evidence_line" | tr ';' '\n' | sed -n "s/^[[:space:]]*${key}=//p" | head -1 | sed 's/[[:space:]]*$//'
}

normalize_token() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]'
}

is_empty_marker() {
  local token
  token="$(normalize_token "$1")"
  [[ -z "$token" || "$token" == "none" || "$token" == "n/a" || "$token" == "na" || "$token" == "null" || "$token" == "-" || "$token" == "non" || "$token" == "aucun" || "$token" == "aucune" ]]
}

is_placeholder_marker() {
  local token
  token="$(normalize_token "$1")"
  [[ "$token" == "?" || "$token" == "??" || "$token" == "???" || "$token" == "tbd" || "$token" == "todo" || "$token" == "to_do" || "$token" == "fixme" || "$token" == "a_faire" || "$token" == "coming_soon" || "$token" == "unknown" || "$token" == "pending" || "$token" == "later" ]]
}

is_weak_value() {
  local raw="$1"
  if is_empty_marker "$raw"; then
    return 0
  fi
  if is_placeholder_marker "$raw"; then
    return 0
  fi
  local compact
  compact="$(printf '%s' "$raw" | tr -d '[:space:]')"
  [[ ${#compact} -lt 3 ]]
}

has_required_kv_markers() {
  local raw="$1"
  shift || true
  local text
  text="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  local key
  for key in "$@"; do
    if ! printf '%s\n' "$text" | grep -Eiq "(^|[;[:space:],])${key}="; then
      return 1
    fi
  done
  return 0
}

reuse_check_valid() {
  local raw="$1"
  local low
  low="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  if is_weak_value "$low"; then
    return 1
  fi
  if [[ "$low" == "none" ]]; then
    return 1
  fi
  if [[ "$low" == none* ]]; then
    [[ "$raw" =~ ^[Nn][Oo][Nn][Ee]\(.{3,}\)$ ]] || return 1
  fi
  return 0
}

channels_missing_streak_24h=0
none_signal_streak_24h=0
contract_guard_block_count_24h=0
issue_reporting_ok_rate_24h=100
issue_reporting_total_24h=0
issue_reporting_ok_count_24h=0
delivery_actions_24h=0
enforced_delivery_count_24h=0
stall_recovery_rate_24h=100
ready_seen_without_claim_24h=0
if [[ -f "$EVENTS_FILE" ]]; then
  metrics_line="$(python3 - "$EVENTS_FILE" <<'PY'
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
cutoff = time.time() - (24 * 3600)
rows = []
for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = raw.strip()
    if not line:
        continue
    try:
        item = json.loads(line)
    except Exception:
        continue
    if not isinstance(item, dict):
        continue
    if str(item.get("role", "")).strip().lower() != "dev":
        continue
    ts_raw = str(item.get("ts_utc", "") or "").strip()
    if ts_raw.endswith("Z"):
        ts_raw = ts_raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ts_raw)
    except Exception:
        continue
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ts_epoch = dt.timestamp()
    if ts_epoch < cutoff:
        continue
    item["_ts"] = ts_epoch
    rows.append(item)

rows.sort(key=lambda r: float(r.get("_ts", 0.0)))

channels_streak = 0
channels_streak_max = 0
none_streak = 0
none_streak_max = 0
guard_blocks = 0
issue_total = 0
issue_ok = 0
delivery_actions = 0
enforced_delivery = 0
ready_seen_without_claim = 0
stall_recovery_count = 0
stall_recovery_base = 0
prev_task_update = ""

for row in rows:
    blocker = str(row.get("blocker_id", "") or "").strip().upper()
    delta = str(row.get("delta", "") or "").strip().upper()
    issues_raw = str(row.get("issues", "") or "").strip().lower()
    codes = [tok.strip() for tok in issues_raw.split(",") if tok.strip()]
    channels_missing = (
        blocker == "CHANNELS_READ_MISSING"
        or "contract_guard_channels_read_missing" in codes
        or "channels_read_missing" in codes
    )
    if channels_missing:
        channels_streak += 1
    else:
        channels_streak = 0
    channels_streak_max = max(channels_streak_max, channels_streak)

    task_update = str(row.get("task_update", "") or "").strip().lower()
    if task_update in {"claim", "complete", "handoff"}:
        delivery_actions += 1
    if "dev_autonomy_enforced" in codes or delta == "DEV_AUTONOMY_ENFORCED_DELIVERY":
        enforced_delivery += 1
    if task_update in {"none_no_signal", "none_no_ready"} and delta == "READY_ITEM_AVAILABLE_RUNTIME_CONTEXT":
        ready_seen_without_claim += 1
    if prev_task_update in {"none_no_signal", "none_no_ready"}:
        stall_recovery_base += 1
        if task_update in {"claim", "complete", "handoff"}:
            stall_recovery_count += 1
    prev_task_update = task_update

    if task_update == "none_no_signal":
        none_streak += 1
    else:
        none_streak = 0
    none_streak_max = max(none_streak_max, none_streak)

    if delta == "CONTRACT_GUARD_BLOCK" or blocker.startswith("CONTRACT_GUARD_"):
        guard_blocks += 1

    issue_total += 1
    if bool(row.get("issue_reporting_ok", False)):
        issue_ok += 1

rate = int(round((issue_ok / issue_total) * 100)) if issue_total > 0 else 100
recovery_rate = int(round((stall_recovery_count / stall_recovery_base) * 100)) if stall_recovery_base > 0 else 100
print(
    f"{channels_streak_max} {none_streak_max} {guard_blocks} "
    f"{rate} {issue_total} {issue_ok} {delivery_actions} {enforced_delivery} {recovery_rate} {ready_seen_without_claim}"
)
PY
)"
  if [[ -n "${metrics_line:-}" ]]; then
    read -r channels_missing_streak_24h none_signal_streak_24h contract_guard_block_count_24h issue_reporting_ok_rate_24h issue_reporting_total_24h issue_reporting_ok_count_24h delivery_actions_24h enforced_delivery_count_24h stall_recovery_rate_24h ready_seen_without_claim_24h <<< "$metrics_line"
  fi
fi

missing=()
invalid=()
run_note="$(ev_get run_note)"
run_note_words="$(printf '%s\n' "$run_note" | awk '{print NF}')"
if [[ "$task_update" == "claim" ]]; then
  for field in root_cause architecture_check vision_alignment reuse_check; do
    val="$(ev_get "$field")"
    if is_weak_value "$val"; then
      missing+=("$field")
    fi
  done
elif [[ "$task_update" == "complete" || "$task_update" == "handoff" ]]; then
  for field in root_cause fix_applied verify reuse_check architecture_check vision_alignment qa_proof; do
    val="$(ev_get "$field")"
    if is_weak_value "$val"; then
      missing+=("$field")
    fi
  done
fi

architecture_check="$(ev_get architecture_check)"
vision_alignment="$(ev_get vision_alignment)"
verify_field="$(ev_get verify)"
qa_proof="$(ev_get qa_proof)"
reuse_check="$(ev_get reuse_check)"

if [[ "$task_update" == "claim" || "$task_update" == "complete" || "$task_update" == "handoff" ]]; then
  if [[ ! " ${missing[*]} " =~ " architecture_check " ]] && ! has_required_kv_markers "$architecture_check" layer imports_ok path_target; then
    invalid+=("architecture_check_format")
  fi
  if [[ ! " ${missing[*]} " =~ " vision_alignment " ]] && ! has_required_kv_markers "$vision_alignment" batch target impact; then
    invalid+=("vision_alignment_format")
  fi
  if [[ ! " ${missing[*]} " =~ " reuse_check " ]] && ! reuse_check_valid "$reuse_check"; then
    invalid+=("reuse_check_format")
  fi
fi

if [[ "$task_update" == "complete" || "$task_update" == "handoff" ]]; then
  if [[ ! " ${missing[*]} " =~ " verify " ]] && ! has_required_kv_markers "$verify_field" before after test; then
    invalid+=("verify_format")
  fi
  if [[ ! " ${missing[*]} " =~ " qa_proof " ]] && ! has_required_kv_markers "$qa_proof" test result; then
    invalid+=("qa_proof_format")
  fi
fi

failures_24h="0"
if [[ -f "$TICK_LOG" ]]; then
  failures_24h="$(python3 - "$TICK_LOG" <<'PY'
import re, sys, time
from datetime import datetime
path = sys.argv[1]
now = int(time.time())
cutoff = now - 24*3600
count = 0
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}).*?\[END\].*?rc=(\d+)', line)
        if not m:
            continue
        ts = int(datetime.fromisoformat(m.group(1)).timestamp())
        if ts < cutoff:
            continue
        if int(m.group(2)) != 0:
            count += 1
print(count)
PY
)"
fi

action_markers="0"
contract_markers="0"
if [[ -f "$TICK_LOG" ]]; then
  action_markers="$(tail -n 600 "$TICK_LOG" | grep -c '\[ACTION\]' || true)"
  contract_markers="$(tail -n 600 "$TICK_LOG" | grep -c '\[CONTRACT\]' || true)"
fi

echo "DEV_PARENT: SNAPSHOT"
echo "status=${status:-?} verdict=${verdict:-?} task_update=${task_update:-?}"
echo "failures_last_24h=${failures_24h}"
echo "tick_markers contract=${contract_markers} action=${action_markers}"
echo "run_note_words=${run_note_words:-0}"
echo "next_action=${next_action:-?}"

if [[ "${#missing[@]}" -gt 0 ]]; then
  echo "coaching_gap_missing=missing_evidence_fields:${missing[*]}"
else
  echo "coaching_gap_missing=none"
fi
if [[ "${#invalid[@]}" -gt 0 ]]; then
  echo "coaching_gap_invalid=invalid_evidence_format:${invalid[*]}"
else
  echo "coaching_gap_invalid=none"
fi

score=100
score=$(( score - (12 * ${#missing[@]}) - (10 * ${#invalid[@]}) ))
if [[ "${run_note_words:-0}" -lt 5 ]]; then
  score=$(( score - 8 ))
fi
if [[ "$score" -lt 0 ]]; then score=0; fi
if [[ "$score" -ge 80 ]]; then
  quality="STRONG"
elif [[ "$score" -ge 55 ]]; then
  quality="MEDIUM"
else
  quality="WEAK"
fi
echo "quality_score=${score}"
echo "quality=${quality}"

coaching_state="DELIVERING"
if [[ "${channels_missing_streak_24h:-0}" -ge 2 || "${contract_guard_block_count_24h:-0}" -ge 2 || "${none_signal_streak_24h:-0}" -ge 3 ]]; then
  coaching_state="STALLED"
elif [[ "$quality" != "STRONG" || "${issue_reporting_ok_rate_24h:-100}" -lt 95 || "${failures_24h:-0}" -gt 0 ]]; then
  coaching_state="RECOVERING"
fi
echo "autonomy_streaks channels_missing_24h=${channels_missing_streak_24h:-0} none_no_signal_24h=${none_signal_streak_24h:-0} contract_guard_blocks_24h=${contract_guard_block_count_24h:-0}"
echo "issue_reporting_ok_rate_24h=${issue_reporting_ok_rate_24h:-100}% (${issue_reporting_ok_count_24h:-0}/${issue_reporting_total_24h:-0})"
echo "delivery_actions_24h=${delivery_actions_24h:-0} enforced_delivery_count_24h=${enforced_delivery_count_24h:-0} stall_recovery_rate_24h=${stall_recovery_rate_24h:-100}% ready_seen_without_claim_24h=${ready_seen_without_claim_24h:-0}"
echo "coaching_state=${coaching_state}"

escalation_active=0
escalation_target_role="none"
escalation_cause="none"
escalation_message="none"
if [[ "${coaching_state:-RECOVERING}" == "STALLED" && "${none_signal_streak_24h:-0}" -ge 3 ]]; then
  escalation_active=1
  if [[ "${channels_missing_streak_24h:-0}" -ge 2 || "${issue_reporting_ok_rate_24h:-100}" -lt 95 ]]; then
    escalation_target_role="dev"
    escalation_cause="contract_format"
    escalation_message="Corriger format EVIDENCE (channels_read impact_assessment impact_action + issue_*) puis relancer claim->patch->test."
  else
    escalation_target_role="planner"
    escalation_cause="dependencies"
    escalation_message="Reevaluer deps et ouvrir runway READY immediat pour dev (claimable sans waiting_dep massif)."
  fi
fi

mkdir -p "$(dirname "$ESCALATION_OUT")"
python3 - "$ESCALATION_OUT" "$escalation_active" "$escalation_target_role" "$escalation_cause" "$escalation_message" "${none_signal_streak_24h:-0}" "${channels_missing_streak_24h:-0}" "${contract_guard_block_count_24h:-0}" "${issue_reporting_ok_rate_24h:-100}" <<'PY' >/dev/null 2>&1 || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
payload = {
    "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "active": str(sys.argv[2]).strip() == "1",
    "target_role": sys.argv[3] or "none",
    "cause": sys.argv[4] or "none",
    "message": sys.argv[5] or "none",
    "none_signal_streak_24h": int(sys.argv[6] or "0"),
    "channels_missing_streak_24h": int(sys.argv[7] or "0"),
    "contract_guard_block_count_24h": int(sys.argv[8] or "0"),
    "issue_reporting_ok_rate_24h": int(sys.argv[9] or "100"),
}
out.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY

coach_note="dev_parent $(date -u +%Y-%m-%dT%H:%M:%SZ) status=${status:-?} task_update=${task_update:-?} missing=${missing[*]:-none} invalid=${invalid[*]:-none} failures_24h=${failures_24h} markers=contract:${contract_markers},action:${action_markers} quality=${quality}:${score} coaching_state=${coaching_state} channels_missing_24h=${channels_missing_streak_24h:-0} none_signal_24h=${none_signal_streak_24h:-0} issue_ok_rate_24h=${issue_reporting_ok_rate_24h:-100}"
if [[ "$APPEND_MEMORY" -eq 1 ]]; then
  mkdir -p "$(dirname "$MEMORY_FILE")"
  if [[ ! -f "$MEMORY_FILE" ]]; then
    printf "# Dev Agent Memory\n\n" > "$MEMORY_FILE"
  fi
  printf -- "- %s\n" "$coach_note" >> "$MEMORY_FILE"
  echo "memory_append=ok file=$MEMORY_FILE"
fi

mkdir -p "$(dirname "$JSON_OUT")"
python3 - "$JSON_OUT" "$status" "$verdict" "$task_update" "$next_action" "$failures_24h" "$contract_markers" "$action_markers" "$run_note_words" "$score" "$quality" "$(IFS=,; echo "${missing[*]}")" "$(IFS=,; echo "${invalid[*]}")" "${channels_missing_streak_24h:-0}" "${none_signal_streak_24h:-0}" "${contract_guard_block_count_24h:-0}" "${issue_reporting_ok_rate_24h:-100}" "${issue_reporting_total_24h:-0}" "${issue_reporting_ok_count_24h:-0}" "${coaching_state:-RECOVERING}" "${delivery_actions_24h:-0}" "${enforced_delivery_count_24h:-0}" "${stall_recovery_rate_24h:-100}" "${ready_seen_without_claim_24h:-0}" <<'PY' >/dev/null 2>&1 || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
payload = {
    "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "status": sys.argv[2] or "?",
    "verdict": sys.argv[3] or "?",
    "task_update": sys.argv[4] or "?",
    "next_action_unique": sys.argv[5] or "?",
    "failures_last_24h": int(sys.argv[6] or "0"),
    "contract_markers": int(sys.argv[7] or "0"),
    "action_markers": int(sys.argv[8] or "0"),
    "run_note_words": int(sys.argv[9] or "0"),
    "quality_score": int(sys.argv[10] or "0"),
    "quality": sys.argv[11] or "WEAK",
    "missing_fields": [x for x in (sys.argv[12] or "").split(",") if x],
    "invalid_fields": [x for x in (sys.argv[13] or "").split(",") if x],
    "channels_missing_streak_24h": int(sys.argv[14] or "0"),
    "none_signal_streak_24h": int(sys.argv[15] or "0"),
    "contract_guard_block_count_24h": int(sys.argv[16] or "0"),
    "issue_reporting_ok_rate_24h": int(sys.argv[17] or "100"),
    "issue_reporting_total_24h": int(sys.argv[18] or "0"),
    "issue_reporting_ok_count_24h": int(sys.argv[19] or "0"),
    "coaching_state": sys.argv[20] or "RECOVERING",
    "delivery_actions_24h": int(sys.argv[21] or "0"),
    "enforced_delivery_count_24h": int(sys.argv[22] or "0"),
    "stall_recovery_rate_24h": int(sys.argv[23] or "100"),
    "ready_seen_without_claim_24h": int(sys.argv[24] or "0"),
}
out.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
echo "json_out=${JSON_OUT}"
echo "escalation_out=${ESCALATION_OUT}"

if [[ "$STRICT" -eq 1 ]]; then
  if [[ "${#missing[@]}" -gt 0 || "${#invalid[@]}" -gt 0 || "$failures_24h" != "0" ]]; then
    echo "strict_verdict=FAIL"
    exit 1
  fi
  if [[ "${run_note_words:-0}" -lt 5 ]]; then
    echo "strict_verdict=FAIL"
    exit 1
  fi
  if [[ "$action_markers" == "0" || "$contract_markers" == "0" ]]; then
    echo "strict_verdict=FAIL"
    exit 1
  fi
  if [[ "${coaching_state:-RECOVERING}" == "STALLED" ]]; then
    echo "strict_verdict=FAIL"
    exit 1
  fi
fi

echo "strict_verdict=PASS"
