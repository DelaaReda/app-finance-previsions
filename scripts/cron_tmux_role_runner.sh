#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

ROLE="${1:-}"
if [[ -z "$ROLE" ]]; then
  echo "Usage: $0 <planner|dev|tester|qa|architect|po|scrum_master|clawsentinel>"
  exit 2
fi

case "$ROLE" in
  planner|dev|tester|qa|architect|po|scrum_master|clawsentinel|analyst|backend_engineer|frontend_engineer|integrator|data_analyst|infra_engineer) ;;
  *)
    echo "Unsupported role: $ROLE"
    exit 3
    ;;
esac

AGENT_BIN="${TMUX_ROLE_AGENT_BIN:-codex}"
AGENT_BIN_NAME="${AGENT_BIN##*/}"
PROMPT_TIMEOUT_SECONDS="${PROMPT_TIMEOUT_SECONDS:-55}"
RETRY_PROMPT_TIMEOUT_SECONDS="${RETRY_PROMPT_TIMEOUT_SECONDS:-20}"
STATE_DIR="${TMUX_ROLE_STATE_DIR:-/home/venom/.openclaw/cron/role-state}"
TRACE_DIR="${TMUX_ROLE_TRACE_DIR:-$ROOT/logs-codex-runs/role-runner}"
ROLE_MEMORY_DIR="${TMUX_ROLE_MEMORY_DIR:-$ROOT/memory/agents}"
TEAM_CHAT_FILE="${TMUX_ROLE_TEAM_CHAT_FILE:-$ROOT/docs/ops/ADMIN_TEAM_CHAT.md}"
TEAM_ITER_FILE="${TMUX_ROLE_TEAM_ITER_FILE:-$ROOT/docs/ops/ADMIN_TEAM_ITERATIONS.md}"
WORKBOARD_FILE="${TMUX_ROLE_WORKBOARD_FILE:-$ROOT/docs/orchestrator-ops/parallel-workstreams.json}"
RECOVERY_THRESHOLD="${TMUX_ROLE_RECOVERY_THRESHOLD:-2}"
SKIP_RETRY_ON_TIMEOUT="${SKIP_RETRY_ON_TIMEOUT:-1}"
RETRY_ENGINE_DEFAULT="${TMUX_ROLE_RETRY_ENGINE_DEFAULT:-tmux}"
NO_DELTA_THRESHOLD="${TMUX_ROLE_NO_DELTA_THRESHOLD:-6}"
TMUX_CAPTURE_LINES="${TMUX_ROLE_CAPTURE_LINES:-2600}"
TMUX_READY_WAIT_SECONDS="${TMUX_ROLE_READY_WAIT_SECONDS:-8}"
TMUX_POLL_INTERVAL_SECONDS="${TMUX_ROLE_POLL_INTERVAL_SECONDS:-1}"
TMUX_STALL_ABORT_SECONDS="${TMUX_ROLE_STALL_ABORT_SECONDS:-18}"
CODEX_EXEC_FALLBACK="${TMUX_ROLE_CODEX_EXEC_FALLBACK:-1}"
CODEX_EXEC_MODEL="${TMUX_ROLE_CODEX_MODEL:-gpt-5.3-codex}"
CODEX_NO_ALT_SCREEN="${TMUX_ROLE_CODEX_NO_ALT_SCREEN:-1}"
CODEX_EXEC_RESUME="${TMUX_ROLE_CODEX_EXEC_RESUME:-0}"
CODEX_SEARCH_ENABLED="${TMUX_ROLE_CODEX_SEARCH_ENABLED:-1}"
CODEX_SANDBOX_MODE="${TMUX_ROLE_CODEX_SANDBOX_MODE:-danger-full-access}"
CODEX_APPROVAL_POLICY="${TMUX_ROLE_CODEX_APPROVAL_POLICY:-never}"
ROLE_ALLOW_FILE_EDITS="${TMUX_ROLE_ALLOW_FILE_EDITS:-auto}"
ALLOW_WORKBOARD_ONLY_DELIVERY="${TMUX_ROLE_ALLOW_WORKBOARD_ONLY_DELIVERY:-0}"
mkdir -p "$STATE_DIR" "$TRACE_DIR"
FAIL_FILE="${STATE_DIR}/${ROLE}.fail_count"
NO_DELTA_FILE="${STATE_DIR}/${ROLE}.no_delta_count"
CODEX_SESSION_FILE="${STATE_DIR}/${ROLE}.codex_exec_session_id"
LAST_CONTRACT_FILE="${STATE_DIR}/${ROLE}.last_contract"
TRACE_FILE="${TRACE_DIR}/${ROLE}.live.log"
LOCK_FILE="${STATE_DIR}/${ROLE}.run.lock"
LOCK_META_FILE="${STATE_DIR}/${ROLE}.run.lock.meta"

if ! [[ "$RECOVERY_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$RECOVERY_THRESHOLD" -lt 1 ]]; then
  RECOVERY_THRESHOLD=2
fi
if ! [[ "$PROMPT_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$PROMPT_TIMEOUT_SECONDS" -lt 1 ]]; then
  PROMPT_TIMEOUT_SECONDS=55
fi
if ! [[ "$RETRY_PROMPT_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$RETRY_PROMPT_TIMEOUT_SECONDS" -lt 1 ]]; then
  RETRY_PROMPT_TIMEOUT_SECONDS=20
fi
if ! [[ "$SKIP_RETRY_ON_TIMEOUT" =~ ^[01]$ ]]; then
  SKIP_RETRY_ON_TIMEOUT=1
fi
if ! [[ "$NO_DELTA_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$NO_DELTA_THRESHOLD" -lt 1 ]]; then
  NO_DELTA_THRESHOLD=6
fi
if ! [[ "$TMUX_CAPTURE_LINES" =~ ^[0-9]+$ ]] || [[ "$TMUX_CAPTURE_LINES" -lt 400 ]]; then
  TMUX_CAPTURE_LINES=2600
fi
if ! [[ "$TMUX_READY_WAIT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TMUX_READY_WAIT_SECONDS" -lt 1 ]]; then
  TMUX_READY_WAIT_SECONDS=8
fi
if ! [[ "$TMUX_POLL_INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TMUX_POLL_INTERVAL_SECONDS" -lt 1 ]]; then
  TMUX_POLL_INTERVAL_SECONDS=1
fi
if ! [[ "$TMUX_STALL_ABORT_SECONDS" =~ ^[0-9]+$ ]]; then
  TMUX_STALL_ABORT_SECONDS=18
fi
if ! [[ "$CODEX_EXEC_FALLBACK" =~ ^[01]$ ]]; then
  CODEX_EXEC_FALLBACK=1
fi
if ! [[ "$CODEX_NO_ALT_SCREEN" =~ ^[01]$ ]]; then
  CODEX_NO_ALT_SCREEN=1
fi
if ! [[ "$CODEX_EXEC_RESUME" =~ ^[01]$ ]]; then
  CODEX_EXEC_RESUME=0
fi
if ! [[ "$CODEX_SEARCH_ENABLED" =~ ^[01]$ ]]; then
  CODEX_SEARCH_ENABLED=1
fi
case "$CODEX_SANDBOX_MODE" in
  read-only|workspace-write|danger-full-access) ;;
  *) CODEX_SANDBOX_MODE="danger-full-access" ;;
esac
case "$CODEX_APPROVAL_POLICY" in
  untrusted|on-failure|on-request|never) ;;
  *) CODEX_APPROVAL_POLICY="never" ;;
esac
if [[ "$ROLE_ALLOW_FILE_EDITS" != "0" && "$ROLE_ALLOW_FILE_EDITS" != "1" && "$ROLE_ALLOW_FILE_EDITS" != "auto" ]]; then
  ROLE_ALLOW_FILE_EDITS="auto"
fi
if ! [[ "$ALLOW_WORKBOARD_ONLY_DELIVERY" =~ ^[01]$ ]]; then
  ALLOW_WORKBOARD_ONLY_DELIVERY=0
fi
if [[ "$RETRY_ENGINE_DEFAULT" != "tmux" && "$RETRY_ENGINE_DEFAULT" != "sdk" ]]; then
  RETRY_ENGINE_DEFAULT="tmux"
fi
if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not available in PATH" >&2
  exit 5
fi
if [[ "${AGENT_BIN_NAME,,}" != "codex" ]]; then
  AGENT_BIN="codex"
  AGENT_BIN_NAME="codex"
fi
if ! command -v "$AGENT_BIN" >/dev/null 2>&1; then
  echo "codex is not available in PATH" >&2
  exit 4
fi
if [[ "${AGENT_BIN_NAME,,}" != "codex" && "$RETRY_ENGINE_DEFAULT" == "sdk" ]]; then
  RETRY_ENGINE_DEFAULT="tmux"
fi

CODEX_EXEC_AVAILABLE=0
CODEX_EXEC_PRIMARY=0
PRIMARY_CHANNEL="tmux"
OUTPUT_CHANNEL_LABEL="tmux"
if [[ "${AGENT_BIN_NAME,,}" == "codex" && "$CODEX_EXEC_FALLBACK" == "1" ]]; then
  CODEX_EXEC_AVAILABLE=1
fi
# Respect tmux history by default; codex_exec is primary only when explicitly requested.
if [[ "$CODEX_EXEC_AVAILABLE" -eq 1 && "$RETRY_ENGINE_DEFAULT" == "sdk" ]]; then
  CODEX_EXEC_PRIMARY=1
  PRIMARY_CHANNEL="codex_exec"
  OUTPUT_CHANNEL_LABEL="codex_exec"
fi
if [[ "$CODEX_EXEC_PRIMARY" -eq 1 ]]; then
  # codex exec resume often needs longer wall time than tmux prompt scraping.
  if [[ "$PROMPT_TIMEOUT_SECONDS" -lt 70 ]]; then
    PROMPT_TIMEOUT_SECONDS=70
  fi
  if [[ "$RETRY_PROMPT_TIMEOUT_SECONDS" -lt 20 ]]; then
    RETRY_PROMPT_TIMEOUT_SECONDS=20
  fi
fi

ROLE_ALLOW_FILE_EDITS_EFFECTIVE=0
if [[ "$ROLE_ALLOW_FILE_EDITS" == "1" ]]; then
  ROLE_ALLOW_FILE_EDITS_EFFECTIVE=1
elif [[ "$ROLE_ALLOW_FILE_EDITS" == "auto" ]]; then
  case "$ROLE" in
    dev|tester|qa|backend_engineer|frontend_engineer|integrator|data_analyst|infra_engineer)
      ROLE_ALLOW_FILE_EDITS_EFFECTIVE=1
      ;;
    *)
      ROLE_ALLOW_FILE_EDITS_EFFECTIVE=0
      ;;
  esac
fi

runtime_queue_has_ready() {
  if [[ ! -f "docs/orchestrator-ops/priority-queue.json" ]]; then
    echo "0"
    return 0
  fi
  jq -r '[.items[]? | select((.state // "")=="READY")] | if length>0 then "1" else "0" end' \
    docs/orchestrator-ops/priority-queue.json 2>/dev/null || echo "0"
}

runtime_workboard_role_has_work() {
  if [[ ! -f "$WORKBOARD_FILE" ]]; then
    echo "0"
    return 0
  fi
  python3 - "$WORKBOARD_FILE" "$ROLE" <<'PY' 2>/dev/null || echo "0"
import json
import sys
from pathlib import Path

board_path = Path(sys.argv[1])
role = sys.argv[2]
try:
    board = json.loads(board_path.read_text(encoding="utf-8"))
except Exception:
    print("0")
    raise SystemExit(0)

states = {"READY", "IN_PROGRESS", "REVIEW"}
for task in board.get("tasks", []):
    if str(task.get("role", "")) != role:
        continue
    if str(task.get("state", "")).upper() in states:
        print("1")
        break
else:
    print("0")
PY
}

runtime_workboard_role_has_in_progress() {
  if [[ ! -f "$WORKBOARD_FILE" ]]; then
    echo "0"
    return 0
  fi
  python3 - "$WORKBOARD_FILE" "$ROLE" <<'PY' 2>/dev/null || echo "0"
import json
import sys
from pathlib import Path

board_path = Path(sys.argv[1])
role = sys.argv[2]
try:
    board = json.loads(board_path.read_text(encoding="utf-8"))
except Exception:
    print("0")
    raise SystemExit(0)

for task in board.get("tasks", []):
    if str(task.get("role", "")) != role:
        continue
    if str(task.get("state", "")).upper() == "IN_PROGRESS":
        print("1")
        break
else:
    print("0")
PY
}

runtime_source_version() {
  local path="$1"
  local prefix="$2"
  local checksum=""
  local mtime=""
  if [[ ! -f "$path" ]]; then
    echo "${prefix}_missing"
    return 0
  fi
  checksum="$(sha256sum "$path" 2>/dev/null | awk '{print $1}' | cut -c1-12)"
  mtime="$(stat -c %Y "$path" 2>/dev/null || echo 0)"
  if [[ -z "$checksum" ]]; then
    checksum="unknown"
  fi
  if [[ ! "$mtime" =~ ^[0-9]+$ ]]; then
    mtime=0
  fi
  echo "${prefix}_${mtime}_${checksum}"
}

RUNTIME_QUEUE_HAS_READY="$(runtime_queue_has_ready)"
if [[ ! "$RUNTIME_QUEUE_HAS_READY" =~ ^[01]$ ]]; then
  RUNTIME_QUEUE_HAS_READY="0"
fi
RUNTIME_WORKBOARD_ROLE_HAS_WORK="$(runtime_workboard_role_has_work)"
if [[ ! "$RUNTIME_WORKBOARD_ROLE_HAS_WORK" =~ ^[01]$ ]]; then
  RUNTIME_WORKBOARD_ROLE_HAS_WORK="0"
fi
RUNTIME_WORKBOARD_ROLE_HAS_IN_PROGRESS="$(runtime_workboard_role_has_in_progress)"
if [[ ! "$RUNTIME_WORKBOARD_ROLE_HAS_IN_PROGRESS" =~ ^[01]$ ]]; then
  RUNTIME_WORKBOARD_ROLE_HAS_IN_PROGRESS="0"
fi
RUNTIME_QUEUE_VERSION="$(runtime_source_version "docs/orchestrator-ops/priority-queue.json" "queue")"
RUNTIME_WORKBOARD_VERSION="$(runtime_source_version "$WORKBOARD_FILE" "workboard")"
# Auto-delivery roles only run in write mode when their lane has actionable work.
if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
  if [[ "$RUNTIME_WORKBOARD_ROLE_HAS_IN_PROGRESS" == "1" ]]; then
    ROLE_ALLOW_FILE_EDITS_EFFECTIVE=1
  elif [[ "$RUNTIME_WORKBOARD_ROLE_HAS_WORK" != "1" ]]; then
    ROLE_ALLOW_FILE_EDITS_EFFECTIVE=0
  elif [[ "$RUNTIME_QUEUE_HAS_READY" == "1" ]]; then
    ROLE_ALLOW_FILE_EDITS_EFFECTIVE=1
  elif [[ "$ALLOW_WORKBOARD_ONLY_DELIVERY" == "1" ]]; then
    ROLE_ALLOW_FILE_EDITS_EFFECTIVE=1
  else
    ROLE_ALLOW_FILE_EDITS_EFFECTIVE=0
  fi
fi

target_session_name() {
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    dev) echo "codex_dev_cron" ;;
    tester) echo "codex_tester_cron" ;;
    qa) echo "codex_qa_cron" ;;
    architect) echo "codex_architect_cron" ;;
    po) echo "codex_po_cron" ;;
    scrum_master) echo "codex_scrum_master_cron" ;;
    analyst) echo "codex_analyst_cron" ;;
    backend_engineer) echo "codex_backend_engineer_cron" ;;
    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
    integrator) echo "codex_integrator_cron" ;;
    data_analyst) echo "codex_data_analyst_cron" ;;
    infra_engineer) echo "codex_infra_engineer_cron" ;;
    manager) echo "codex_manager_cron" ;;
    clawsentinel) echo "clawsentinel" ;;
  esac
}

agent_launch_command() {
  if [[ "${AGENT_BIN_NAME,,}" != "codex" ]]; then
    printf '%s' "$AGENT_BIN"
    return 0
  fi
  local cmd="$AGENT_BIN"
  if [[ "$CODEX_NO_ALT_SCREEN" == "1" ]]; then
    cmd="${cmd} --no-alt-screen"
  fi
  cmd="${cmd} --sandbox ${CODEX_SANDBOX_MODE} -a ${CODEX_APPROVAL_POLICY}"
  if [[ "$CODEX_SEARCH_ENABLED" == "1" ]]; then
    cmd="${cmd} --search"
  fi
  printf '%s' "$cmd"
}

build_codex_global_args() {
  local -a args=()
  args+=(--sandbox "$CODEX_SANDBOX_MODE" -a "$CODEX_APPROVAL_POLICY")
  if [[ "$CODEX_SEARCH_ENABLED" == "1" ]]; then
    args+=(--search)
  fi
  printf '%s\n' "${args[@]}"
}

health_roles() {
  printf '%s\n' planner analyst architect backend_engineer frontend_engineer data_analyst infra_engineer integrator dev tester qa po scrum_master clawsentinel
}

trace_event() {
  local msg="$1"
  printf '%s role=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ROLE" "$msg" >> "$TRACE_FILE"
}

one_line() {
  printf '%s' "$1" | tr '\n' ' ' | tr -s ' ' | cut -c1-180
}

ensure_role_memory_file() {
  local path="${ROLE_MEMORY_DIR}/${ROLE}.md"
  mkdir -p "$ROLE_MEMORY_DIR"
  if [[ -f "$path" ]]; then
    return 0
  fi
  cat > "$path" <<EOF
# Agent Memory: ${ROLE}

- Role focus:
- Stable decisions:
- Useful commands:
- Recurring blockers:
- Handoff expectations:
EOF
}

compact_file_tail() {
  local path="$1"
  local lines="$2"
  local max_chars="$3"
  if [[ ! -f "$path" ]]; then
    printf 'none'
    return 0
  fi
  tail -n "$lines" "$path" 2>/dev/null \
    | tr '\n' ' ' \
    | tr -s ' ' \
    | sed -E 's/[[:space:]]+/ /g' \
    | cut -c1-"$max_chars"
}

read_last_contract_hint() {
  local path="$1"
  local scope="$2"
  local status=""
  local delta=""
  local next_action=""
  if [[ ! -f "$path" ]]; then
    printf '%s:none' "$scope"
    return 0
  fi
  status="$(sed -n 's/^STATUS:[[:space:]]*//p' "$path" | head -n 1 | tr -s ' ' | tr '\n' ' ')"
  delta="$(sed -n 's/^DELTA:[[:space:]]*//p' "$path" | head -n 1 | tr -s ' ' | tr '\n' ' ')"
  next_action="$(sed -n 's/^NEXT_ACTION_UNIQUE:[[:space:]]*//p' "$path" | head -n 1 | tr -s ' ' | tr '\n' ' ')"
  printf '%s:status=%s,delta=%s,next=%s' \
    "$scope" \
    "${status:-unknown}" \
    "${delta:-unknown}" \
    "${next_action:-unknown}"
}

peer_contracts_hint() {
  local role_file=""
  local role_name=""
  local hint=""
  local count=0
  local parts=()
  while IFS= read -r role_file; do
    role_name="$(basename "$role_file" .last_contract)"
    [[ -z "$role_name" || "$role_name" == "$ROLE" ]] && continue
    hint="$(read_last_contract_hint "$role_file" "$role_name")"
    parts+=("$hint")
    count=$((count + 1))
    if [[ "$count" -ge 5 ]]; then
      break
    fi
  done < <(ls -1t "$STATE_DIR"/*.last_contract 2>/dev/null || true)

  if [[ "${#parts[@]}" -eq 0 ]]; then
    printf 'none'
    return 0
  fi
  (IFS='; '; printf '%s' "${parts[*]}") | cut -c1-600
}

workboard_context_hint() {
  if [[ ! -x "scripts/parallel_workstream.py" ]]; then
    printf 'none'
    return 0
  fi
  python3 scripts/parallel_workstream.py context --role "$ROLE" --limit 3 2>/dev/null \
    | tr '\n' ' ' \
    | tr -s ' ' \
    | cut -c1-520
}

persist_last_contract() {
  local payload="$1"
  printf '%s\n' "$payload" > "$LAST_CONTRACT_FILE"
}

acquire_role_lock() {
  local holder_meta=""
  if ! command -v flock >/dev/null 2>&1; then
    return 0
  fi
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    if [[ -f "$LOCK_META_FILE" ]]; then
      holder_meta="$(one_line "$(cat "$LOCK_META_FILE" 2>/dev/null || true)")"
    else
      holder_meta="unknown_holder"
    fi
    cat <<EOF
STATUS: IN_PROGRESS
DELTA: LOCK_SKIP
EVIDENCE: overlapping_run_detected=1; lock_file=${LOCK_FILE}; holder=${holder_meta}
RISKS: concurrence role-runner, risque de timeout et de sorties croisées
NEXT: laisser finir le run en cours puis reprendre au prochain tick
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: RUN_LOCK_BUSY
NEXT_ACTION_UNIQUE: WAIT_RUN_LOCK_${ROLE}_$(date +%s)
EOF
    exit 0
  fi
  printf 'pid=%s host=%s start_utc=%s role=%s\n' "$$" "${HOSTNAME:-unknown}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ROLE" > "$LOCK_META_FILE"
  trap 'rm -f "$LOCK_META_FILE"' EXIT
}

acquire_role_lock

ensure_role_memory_file

sanitize_evidence_fragment() {
  local text="$1"
  printf '%s' "$text" \
    | tr '\n' ' ' \
    | tr -s ' ' \
    | sed -E \
      -e 's/STATUS[[:space:]]*:/STATUS=/g' \
      -e 's/DELTA[[:space:]]*:/DELTA=/g' \
      -e 's/EVIDENCE[[:space:]]*:/EVIDENCE=/g' \
      -e 's/RISKS[[:space:]]*:/RISKS=/g' \
      -e 's/NEXT[[:space:]]*:/NEXT=/g' \
      -e 's/VERDICT[[:space:]]*:/VERDICT=/g' \
      -e 's/BLOCKER_ID[[:space:]]*:/BLOCKER_ID=/g' \
      -e 's/NEXT_ACTION_UNIQUE[[:space:]]*:/NEXT_ACTION_UNIQUE=/g'
}

read_fail_count() {
  if [[ -f "$FAIL_FILE" ]]; then
    cat "$FAIL_FILE"
  else
    echo "0"
  fi
}

write_fail_count() {
  printf '%s\n' "$1" > "$FAIL_FILE"
}

read_no_delta_count() {
  if [[ -f "$NO_DELTA_FILE" ]]; then
    cat "$NO_DELTA_FILE"
  else
    echo "0"
  fi
}

write_no_delta_count() {
  printf '%s\n' "$1" > "$NO_DELTA_FILE"
}

read_codex_session_id() {
  if [[ -f "$CODEX_SESSION_FILE" ]]; then
    tr -d '[:space:]' < "$CODEX_SESSION_FILE"
  else
    printf ''
  fi
}

write_codex_session_id() {
  local sid="$1"
  if [[ -n "$sid" ]]; then
    printf '%s\n' "$sid" > "$CODEX_SESSION_FILE"
  fi
}

clear_codex_session_id() {
  rm -f "$CODEX_SESSION_FILE"
}

apply_no_delta_gate() {
  local payload="$1"
  local source="$2"
  local no_delta=0
  local streak=0
  if printf '%s\n' "$payload" | rg -q '^DELTA:[[:space:]]*NO_DELTA([[:space:]]*)$'; then
    no_delta=1
  fi
  if [[ "$no_delta" -eq 1 ]]; then
    if [[ "${RUNTIME_QUEUE_HAS_READY:-0}" != "1" ]]; then
      # NO_DELTA is expected while no queue item is READY; avoid false escalation.
      write_no_delta_count 0
      printf '%s\n' "$payload"
      return 0
    fi
    streak="$(( $(read_no_delta_count) + 1 ))"
    write_no_delta_count "$streak"
  else
    write_no_delta_count 0
    printf '%s\n' "$payload"
    return 0
  fi
  if [[ "$streak" -ge "$NO_DELTA_THRESHOLD" ]]; then
    cat <<EOF
STATUS: BLOCKED
DELTA: NO_DELTA
EVIDENCE: no_delta_streak=${streak}/${NO_DELTA_THRESHOLD}; gate_source=${source}
RISKS: aucune progression détectée, boucle improductive
NEXT: escalader et corriger prompts/cadence avant prochain tick
VERDICT: BLOCKED
BLOCKER_ID: NO_PROGRESS_STREAK
NEXT_ACTION_UNIQUE: ESCALATE_NO_PROGRESS_${ROLE}
EOF
    return 0
  fi
  printf '%s\n' "$payload"
}

enforce_role_delivery_contract() {
  local source="${1:-unknown}"
  local tmp=""
  tmp="$(mktemp)"
  cat > "$tmp"
  python3 - "$ROLE" "$source" "$tmp" "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" "$RUNTIME_WORKBOARD_ROLE_HAS_WORK" "$RUNTIME_WORKBOARD_ROLE_HAS_IN_PROGRESS" "$RUNTIME_QUEUE_VERSION" "$RUNTIME_WORKBOARD_VERSION" <<'PY'
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

role = sys.argv[1]
source = sys.argv[2]
payload_path = Path(sys.argv[3])
allow_file_edits = sys.argv[4] == "1"
workboard_role_has_work = sys.argv[5] == "1"
workboard_role_has_in_progress = sys.argv[6] == "1"
runtime_queue_version = sys.argv[7]
runtime_workboard_version = sys.argv[8]
text = payload_path.read_text(encoding="utf-8", errors="ignore")

keys = [
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
]

values = {k: "" for k in keys}
for raw in text.splitlines():
    line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
    if not line or ":" not in line:
        continue
    key, val = line.split(":", 1)
    key = key.strip().upper()
    if key in values and not values[key]:
        values[key] = val.strip()

if any(not values[k] for k in keys):
    # If payload is not a full contract, keep original flow unchanged.
    print(text.strip())
    sys.exit(0)

def parse_evidence_kv(raw: str) -> dict:
    out = {}
    for fragment in raw.split(";"):
        item = fragment.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key_norm = key.strip().lower()
        if not key_norm:
            continue
        out[key_norm] = value.strip()
    return out

def append_evidence(raw: str, fragment: str) -> str:
    base = (raw or "").strip(" ;")
    frag = fragment.strip(" ;")
    if not frag:
        return base
    if not base:
        return frag
    if frag.lower() in base.lower():
        return base
    return f"{base}; {frag}"

def is_skip_with_reason(value: str) -> bool:
    v = (value or "").strip()
    upper = v.upper()
    return upper.startswith("SKIP(") and v.endswith(")") and len(v) > len("SKIP()")

def looks_like_permission_error(value: str) -> bool:
    upper = (value or "").strip().upper()
    markers = (
        "PERMISSION DENIED",
        "READ_ONLY",
        "READ-ONLY",
        "NON_ECRIVABLE",
        "WRITE_DENIED",
        "EROFS",
        "EPERM",
    )
    return any(marker in upper for marker in markers)

queue_states = {}
ready_ids = set()
queue_path = Path("docs/orchestrator-ops/priority-queue.json")
if queue_path.exists():
    try:
        queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
        for item in queue_obj.get("items", []):
            item_id = str(item.get("id", "")).strip().upper()
            state = str(item.get("state", "")).strip().upper()
            if item_id:
                queue_states[item_id] = state
            if item_id and state == "READY":
                ready_ids.add(item_id)
    except Exception:
        pass
queue_has_ready = bool(ready_ids)

def emit_blocked(blocker_id: str, reason: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    blocked = {
        "STATUS": "BLOCKED",
        "DELTA": "ROLE_OUTPUT_NOT_SPECIFIC",
        "EVIDENCE": reason,
        "RISKS": "livraison de role non spécifique, iteration non fiable",
        "NEXT": "regenerer une sortie avec preuve explicite liée au role et artefact concret",
        "VERDICT": "BLOCKED",
        "BLOCKER_ID": blocker_id,
        "NEXT_ACTION_UNIQUE": f"FIX_ROLE_CONTRACT_{role.upper()}_{now}",
    }
    print("\n".join(f"{k}: {blocked[k]}" for k in keys))
    sys.exit(0)

status_u = values["STATUS"].upper()
blocker_id_u = values["BLOCKER_ID"].strip().upper()
if status_u == "BLOCKED" and blocker_id_u in {"", "NONE", "N/A", "NULL"}:
    emit_blocked(
        "BLOCKER_ID_MISSING",
        f"role={role}; source={source}; required=BLOCKER_ID != NONE when STATUS=BLOCKED",
    )

role_tokens = {
    "planner": ["QUEUE", "READY", "PRIOR", "WORKSTATE", "PLAN"],
    "analyst": ["ANALYSIS", "REQUIREMENT", "ASSUMPTION", "TASK_ID", "DISCOVERY"],
    "dev": ["TASK", "STOR", "PATCH", "FILE=", "IMPLEMENT", "CODE"],
    "backend_engineer": ["BACKEND", "API", "ENDPOINT", "TASK_ID", "PATCH", "SERVICE"],
    "frontend_engineer": ["FRONTEND", "UI", "COMPONENT", "TASK_ID", "PATCH", "SCREEN"],
    "integrator": ["INTEGRATION", "TASK_ID", "CONTRACT", "E2E", "MERGE", "PIPELINE"],
    "data_analyst": ["DATA", "METRIC", "TASK_ID", "QUERY", "MODEL", "QUALITY"],
    "infra_engineer": ["INFRA", "CI", "DEPLOY", "TASK_ID", "OBSERVABILITY", "PIPELINE"],
    "tester": ["TEST", "PYTEST", "CASE", "SCENARIO", "COVER"],
    "qa": ["QA", "GATE", "VERDICT", "BLOCKER", "COHER"],
    "architect": ["ARCH", "CONTRAIN", "DEPEND", "RISK", "DESIGN", "CONFORMANCE", "ARCH_RULE", "VIOLATION"],
    "po": ["PO", "BACKLOG", "PRIOR", "SCOPE", "VALEUR", "VALUE"],
    "scrum_master": ["SCRUM", "SPRINT", "WIP", "BLOCKER", "CADENCE", "FLOW"],
    "clawsentinel": ["SENTINEL", "CRON", "HEALTH", "DRIFT", "WATCHDOG", "RISK"],
}

artifact_markers = {
    "planner": "PLANNER_ARTIFACT=",
    "analyst": "ANALYST_ARTIFACT=",
    "dev": "DEV_ARTIFACT=",
    "backend_engineer": "BACKEND_ARTIFACT=",
    "frontend_engineer": "FRONTEND_ARTIFACT=",
    "integrator": "INTEGRATOR_ARTIFACT=",
    "data_analyst": "DATA_ARTIFACT=",
    "infra_engineer": "INFRA_ARTIFACT=",
    "tester": "TESTER_ARTIFACT=",
    "qa": "QA_ARTIFACT=",
    "architect": "ARCHITECT_ARTIFACT=",
    "po": "PO_ARTIFACT=",
    "scrum_master": "SCRUM_ARTIFACT=",
    "clawsentinel": "SENTINEL_ARTIFACT=",
}

tokens = role_tokens.get(role, [])
required_marker = artifact_markers.get(role, "ROLE_ARTIFACT=")
required_artifact_key = required_marker.rstrip("=").lower()
evidence_raw = values.get("EVIDENCE", "").strip()
evidence_kv = parse_evidence_kv(evidence_raw)
task_update = evidence_kv.get("task_update", "").strip().lower()
lock_check = evidence_kv.get("lock_check", "").strip().lower()

if not evidence_kv:
    emit_blocked(
        "EVIDENCE_KV_FORMAT_MISSING",
        f"role={role}; source={source}; required=format key=value;key2=value2 in EVIDENCE",
    )

allowed_task_updates = {
    "claim",
    "complete",
    "handoff",
    "blocked",
    "analysis_only",
    "none_no_ready",
    "none_no_signal",
}
if not task_update:
    emit_blocked(
        "TASK_UPDATE_MISSING",
        f"role={role}; source={source}; required=task_update in EVIDENCE",
    )
if task_update and task_update not in allowed_task_updates:
    emit_blocked(
        "TASK_UPDATE_INVALID",
        f"role={role}; source={source}; task_update={task_update}; allowed={','.join(sorted(allowed_task_updates))}",
    )
if role in {"planner", "analyst", "architect", "po", "scrum_master", "clawsentinel"} and (not allow_file_edits) and task_update in {"claim", "complete", "handoff"}:
    emit_blocked(
        "READ_ONLY_TASK_UPDATE_INVALID",
        f"role={role}; source={source}; task_update={task_update}; mode=read_only; allowed=analysis_only|blocked|none_no_ready|none_no_signal",
    )
if lock_check != "ok":
    emit_blocked(
        "LOCK_CHECK_MISSING",
        f"role={role}; source={source}; required=lock_check=ok in EVIDENCE",
    )

if allow_file_edits and workboard_role_has_in_progress and task_update in {"analysis_only", "none_no_ready", "none_no_signal"}:
    emit_blocked(
        "IN_PROGRESS_NO_RESUME",
        f"role={role}; source={source}; task_update={task_update}; required=claim|complete|blocked|handoff when workboard_in_progress=1",
    )

has_artifact_marker = required_marker in values.get("EVIDENCE", "").upper() or bool(evidence_kv.get(required_artifact_key))
if not has_artifact_marker:
    emit_blocked(
        "ROLE_ARTIFACT_MISSING",
        f"role={role}; source={source}; required_marker={required_marker}",
    )

role_required_evidence_keys = {
    "planner": ("vision_rule", "conformance"),
    "architect": ("arch_rule", "conformance", "review_scope", "violations"),
}
required_evidence_keys = role_required_evidence_keys.get(role, tuple())
if required_evidence_keys:
    missing_required = [k for k in required_evidence_keys if not evidence_kv.get(k, "").strip()]
    if missing_required:
        emit_blocked(
            "ROLE_MENTOR_EVIDENCE_MISSING",
            f"role={role}; source={source}; missing={','.join(missing_required)}; required={','.join(required_evidence_keys)}",
        )

if role == "planner":
    conformance = evidence_kv.get("conformance", "").strip().upper()
    if conformance not in {"PASS", "WARN", "BLOCKED"}:
        emit_blocked(
            "PLANNER_CONFORMANCE_INVALID",
            f"role={role}; source={source}; conformance={conformance or 'missing'}; allowed=PASS,WARN,BLOCKED",
        )
    if (queue_has_ready or workboard_role_has_in_progress) and not evidence_kv.get("task_id", "").strip():
        emit_blocked(
            "PLANNER_TASK_ID_MISSING",
            f"role={role}; source={source}; required=task_id when queue_ready=1 or workboard_in_progress=1",
        )

if role == "architect":
    conformance = evidence_kv.get("conformance", "").strip().upper()
    if conformance not in {"PASS", "WARN", "BLOCKED"}:
        emit_blocked(
            "ARCHITECT_CONFORMANCE_INVALID",
            f"role={role}; source={source}; conformance={conformance or 'missing'}; allowed=PASS,WARN,BLOCKED",
        )
    if (queue_has_ready or workboard_role_has_in_progress) and not evidence_kv.get("task_id", "").strip():
        emit_blocked(
            "ARCHITECT_TASK_ID_MISSING",
            f"role={role}; source={source}; required=task_id when queue_ready=1 or workboard_in_progress=1",
        )

if not evidence_kv.get("queue_version", "").strip():
    values["EVIDENCE"] = append_evidence(values.get("EVIDENCE", ""), f"queue_version={runtime_queue_version}")
    evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))
if not evidence_kv.get("workboard_version", "").strip():
    values["EVIDENCE"] = append_evidence(values.get("EVIDENCE", ""), f"workboard_version={runtime_workboard_version}")
    evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))
if not evidence_kv.get("coordination_ref", "").strip():
    coord_task = evidence_kv.get("task_id", "").strip() or "none"
    values["EVIDENCE"] = append_evidence(values.get("EVIDENCE", ""), f"coordination_ref={task_update}:{coord_task}")
    evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))

if status_u == "BLOCKED":
    print("\n".join(f"{k}: {values[k]}" for k in keys))
    sys.exit(0)

# Phase 1 (SHOULD): when work exists, ask for stream/task IDs without blocking the role.
if queue_has_ready or workboard_role_has_work:
    phase1_missing = [k for k in ("stream_id", "task_id") if not evidence_kv.get(k, "").strip()]
    if phase1_missing:
        values["EVIDENCE"] = append_evidence(values.get("EVIDENCE", ""), f"phase1_should_missing={','.join(phase1_missing)}")
        evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))

# Phase 2 (MUST): completion claims must include stream/task + cmd/tests evidence (or SKIP(reason)).
if task_update == "complete":
    missing_phase2 = [k for k in ("stream_id", "task_id") if not evidence_kv.get(k, "").strip()]
    cmd_value = evidence_kv.get("cmd", "").strip()
    tests_value = evidence_kv.get("tests_run", "").strip()
    if not cmd_value:
        missing_phase2.append("cmd")
    elif cmd_value.upper().startswith("SKIP(") and not is_skip_with_reason(cmd_value):
        missing_phase2.append("cmd_skip_reason")
    if not tests_value:
        missing_phase2.append("tests_run")
    elif tests_value.upper().startswith("SKIP(") and not is_skip_with_reason(tests_value):
        missing_phase2.append("tests_run_skip_reason")
    if missing_phase2:
        emit_blocked(
            "EVIDENCE_PHASE2_MISSING",
            f"role={role}; source={source}; task_update=complete; missing={','.join(missing_phase2)}",
        )

if task_update in {"claim", "handoff"}:
    missing_phase_claim = [k for k in ("stream_id", "task_id") if not evidence_kv.get(k, "").strip()]
    if missing_phase_claim:
        emit_blocked(
            "EVIDENCE_PHASE2_MISSING",
            f"role={role}; source={source}; task_update={task_update}; missing={','.join(missing_phase_claim)}",
        )

if task_update == "handoff":
    handoff_to = evidence_kv.get("handoff_to", "").strip()
    if not handoff_to:
        emit_blocked(
            "HANDOFF_TO_MISSING",
            f"role={role}; source={source}; required=handoff_to for task_update=handoff",
        )
    valid_roles = set(role_tokens.keys())
    if handoff_to and handoff_to not in valid_roles:
        emit_blocked(
            "HANDOFF_TO_INVALID",
            f"role={role}; source={source}; handoff_to={handoff_to}; allowed={','.join(sorted(valid_roles))}",
        )
    if not evidence_kv.get("handoff_ref", "").strip() and not evidence_kv.get("handoff_id", "").strip():
        values["EVIDENCE"] = append_evidence(values.get("EVIDENCE", ""), "handoff_ref=pending")
        evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))

scope_text = " ".join(
    [values["DELTA"], values["EVIDENCE"], values["RISKS"], values["NEXT"], values["NEXT_ACTION_UNIQUE"]]
).upper()
has_role_signal = any(tok in scope_text for tok in tokens)
chain_targets = set(re.findall(r"BATCH-[0-9]+", scope_text))
is_generic_dispatch = (
    "DISPATCH_BATCH" in scope_text
    or "LANCER" in scope_text and "DISPATCH" in scope_text
    or "READY_DETECTE" in scope_text
)
target_ready = any(queue_states.get(t, "") == "READY" for t in chain_targets)
permission_claimed = looks_like_permission_error(scope_text)

# Reject stale dispatch actions when runtime queue no longer has READY.
if is_generic_dispatch and not queue_has_ready:
    emit_blocked(
        "STALE_READY_ACTION",
        f"role={role}; source={source}; queue_ready=0; observed_dispatch={','.join(sorted(chain_targets)) or 'none'}",
    )
if is_generic_dispatch and chain_targets and not target_ready:
    emit_blocked(
        "STALE_READY_ACTION",
        f"role={role}; source={source}; queue_ready_ids={','.join(sorted(ready_ids)) or 'none'}; observed_dispatch={','.join(sorted(chain_targets))}",
    )

# Delivery roles must provide real execution evidence when an item is READY.
if role in {"dev", "backend_engineer", "frontend_engineer", "integrator", "data_analyst", "infra_engineer", "tester", "qa"} and allow_file_edits and queue_has_ready:
    has_cmd_evidence = any(
        token in scope_text
        for token in ("CMD=", "COMMAND=", "EXEC_SAFE.SH", "PYTEST", "BACKEND_REGRESSION_GATE", "CURL ", "NPM ", "PNPM ", "YARN ", "UV ", "MAKE ")
    )
    if values["DELTA"].strip().upper() == "NO_DELTA":
        emit_blocked(
            "DELIVERY_NO_DELTA_WITH_READY",
            f"role={role}; source={source}; queue_ready_ids={','.join(sorted(ready_ids))}; delta=NO_DELTA",
        )
    if not has_cmd_evidence:
        emit_blocked(
            "ROLE_EXEC_EVIDENCE_MISSING",
            f"role={role}; source={source}; required=CMD evidence for delivery role; queue_ready_ids={','.join(sorted(ready_ids))}",
        )

if role in {"dev", "backend_engineer", "frontend_engineer", "integrator", "data_analyst", "infra_engineer", "tester", "qa"} and allow_file_edits and task_update == "blocked" and permission_claimed:
    cmd_value = evidence_kv.get("cmd", "").strip()
    cmd_err_excerpt = evidence_kv.get("cmd_err_excerpt", "").strip()
    if not (looks_like_permission_error(cmd_value) or looks_like_permission_error(cmd_err_excerpt)):
        emit_blocked(
            "PERMISSION_BLOCKER_UNVERIFIED",
            f"role={role}; source={source}; required=cmd or cmd_err_excerpt with permission_denied evidence",
        )
    writable_refs = []
    for ref_path in (Path("docs/orchestrator-ops/parallel-workstreams.json"), Path("docs/planning/tasks.md")):
        try:
            if ref_path.exists() and os.access(ref_path, os.W_OK):
                writable_refs.append(str(ref_path))
        except Exception:
            continue
    if writable_refs:
        emit_blocked(
            "PERMISSION_BLOCKER_UNVERIFIED",
            f"role={role}; source={source}; writable_refs={','.join(writable_refs)}; required=continue_delivery_or_real_permission_error",
        )

cmd_value_norm = evidence_kv.get("cmd", "").strip()
if "/home/venom/shared/analyse-financiere" in cmd_value_norm:
    # In the UTM VM the workspace root is often a symlink:
    #   /home/venom/analyse-financiere -> /home/venom/shared/analyse-financiere
    # Treat the shared path as an allowed alias, not a blocker.
    values["EVIDENCE"] = append_evidence(values.get("EVIDENCE", ""), "workdir_alias=shared_ok")
    evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))

# Task/lock hygiene must stay explicit when work exists.
if (queue_has_ready or workboard_role_has_work) and role in {
    "planner",
    "analyst",
    "architect",
    "dev",
    "backend_engineer",
    "frontend_engineer",
    "integrator",
    "data_analyst",
    "infra_engineer",
    "tester",
    "qa",
    "po",
    "scrum_master",
    "clawsentinel",
}:
    if not task_update:
        emit_blocked(
            "TASK_UPDATE_MISSING",
            f"role={role}; source={source}; required=task_update marker when queue_or_workboard_has_work=1",
        )
    if lock_check != "ok":
        emit_blocked(
            "LOCK_CHECK_MISSING",
            f"role={role}; source={source}; required=lock_check=ok marker when queue_or_workboard_has_work=1",
        )

# Keep anti-generic guard, but allow richer role evidence to pass.
has_runtime_context = any(sig in scope_text for sig in ["RUNTIME_CONTEXT", "QUEUE_STATES", "BATCH-"])
generic_dispatch_weak = (
    is_generic_dispatch
    and role in {"tester", "qa", "architect", "po", "scrum_master", "clawsentinel", "analyst", "backend_engineer", "frontend_engineer", "integrator", "data_analyst", "infra_engineer"}
    and len(scope_text) < 260
    and not has_runtime_context
)

if has_role_signal and has_artifact_marker and not generic_dispatch_weak:
    print("\n".join(f"{k}: {values[k]}" for k in keys))
    sys.exit(0)

obs = re.sub(r"\s+", " ", scope_text).strip()[:140]
required = "|".join(tokens) if tokens else "ROLE_SPECIFIC_SIGNAL"
emit_blocked(
    "ROLE_CONTRACT_MISSING",
    f"role={role}; source={source}; required_any={required}; required_marker={required_marker}; observed={obs}",
)
PY
  rm -f "$tmp"
}

reconcile_runtime_truth() {
  local tmp=""
  tmp="$(mktemp)"
  cat > "$tmp"
  python3 - "$ROLE" "$tmp" <<'PY'
import json
import re
import sys
from pathlib import Path

role = sys.argv[1]
payload_path = Path(sys.argv[2])
text = payload_path.read_text(encoding="utf-8", errors="ignore")

keys = [
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
]

values = {k: "" for k in keys}
for raw in text.splitlines():
    line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
    if not line or ":" not in line:
        continue
    key, val = line.split(":", 1)
    key = key.strip().upper()
    if key in values and not values[key]:
        values[key] = val.strip()

queue_has_ready = False
ready_actions = []
queue_states = {}
queue_path = Path("docs/orchestrator-ops/priority-queue.json")
if queue_path.exists():
    try:
        queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
        for item in queue_obj.get("items", []):
            item_id = str(item.get("id", "")).strip()
            state = str(item.get("state", "")).strip()
            if item_id:
                queue_states[item_id] = state
            if state == "READY":
                queue_has_ready = True
                action = str(item.get("next_action", "")).strip()
                if item_id and action:
                    ready_actions.append(f"{item_id}:{action}")
                elif item_id:
                    ready_actions.append(f"{item_id}:NEXT_ACTION_MISSING")
    except Exception:
        pass

batch01_signoff_pass = False
gate_dir = Path("finance-app/openclaw-gates")
if gate_dir.exists():
    for md in sorted(gate_dir.glob("batch-01-*.md")):
        try:
            gate_text = md.read_text(encoding="utf-8", errors="ignore").upper()
        except Exception:
            continue
        if "QA_SIGNOFF: YES" in gate_text and "VERDICT: PASS" in gate_text:
            batch01_signoff_pass = True
            break

delta = values.get("DELTA", "").strip().upper()
if queue_has_ready and delta == "NO_DELTA":
    values["DELTA"] = "READY_ITEM_AVAILABLE_RUNTIME_CONTEXT"
    if ready_actions:
        values["NEXT"] = f"executer action READY: {ready_actions[0]}"
    status = values.get("STATUS", "").strip().upper()
    verdict = values.get("VERDICT", "").strip().upper()
    blocker = values.get("BLOCKER_ID", "").strip().upper()
    if status == "BLOCKED" and blocker in {"NONE", "NO_PROGRESS_STREAK"}:
        values["STATUS"] = "IN_PROGRESS"
    if verdict == "BLOCKED" and blocker in {"NONE", "NO_PROGRESS_STREAK"}:
        values["VERDICT"] = "GO_WITH_CAUTION"

stale_blockers = {
    "QA_PASS_SIGNATURE_UNVERIFIED",
    "MISSING_BATCH01_MD_ARTEFACTS",
    "BATCH01_INVALID_STATE_IN_SPRINT",
    "BATCH01_INVALID_STATE_IN_SPRINT_AND_MISSING_BATCH01_MD",
}
blocker = values.get("BLOCKER_ID", "").strip().upper()
b01_pass = queue_states.get("BATCH-01", "").upper() == "PASS"
b02_ready = queue_states.get("BATCH-02", "").upper() == "READY"
if blocker in stale_blockers and b01_pass and b02_ready and batch01_signoff_pass:
    values["BLOCKER_ID"] = "NONE"
    if values.get("STATUS", "").strip().upper() == "BLOCKED":
        values["STATUS"] = "IN_PROGRESS"
    if values.get("VERDICT", "").strip().upper() == "BLOCKED":
        values["VERDICT"] = "GO_WITH_CAUTION"
    evidence = values.get("EVIDENCE", "").strip()
    suffix = "stale_blocker_filtered_by_runtime_truth"
    if suffix.lower() not in evidence.lower():
        values["EVIDENCE"] = (evidence + "; " + suffix).strip(" ;")

# Canonicalize malformed blocker field like "NONE|QUEUE=..."
blocker_raw = values.get("BLOCKER_ID", "").strip()
blocker_up = blocker_raw.upper()
for clear in ("NONE", "AUCUN"):
    if blocker_up.startswith(clear + "|") or blocker_up.startswith(clear + ";") or blocker_up.startswith(clear + ",") or blocker_up.startswith(clear + " "):
        tail = blocker_raw[len(clear):].strip(" |;,")
        values["BLOCKER_ID"] = clear
        if tail:
            evidence = values.get("EVIDENCE", "").strip()
            suffix = f"blocker_context={tail}"
            if suffix.lower() not in evidence.lower():
                values["EVIDENCE"] = (evidence + "; " + suffix).strip(" ;")
        break

action_text = " ".join(
    [
        values.get("DELTA", ""),
        values.get("EVIDENCE", ""),
        values.get("NEXT", ""),
        values.get("NEXT_ACTION_UNIQUE", ""),
    ]
).upper()
action_targets = set(re.findall(r"BATCH-[0-9]+", action_text))
dispatch_signal = (
    "DISPATCH_BATCH" in action_text
    or ("LANCER" in action_text and "DISPATCH" in action_text)
    or "READY_DETECTE" in action_text
)
if dispatch_signal:
    if not queue_has_ready:
        values["STATUS"] = "BLOCKED"
        values["VERDICT"] = "BLOCKED"
        values["BLOCKER_ID"] = "STALE_READY_ACTION"
        values["RISKS"] = "action de dispatch detectee alors que queue_has_ready=0"
        values["NEXT"] = "rafraichir queue puis proposer une action non-stale"
    elif action_targets and not any(queue_states.get(t, "").upper() == "READY" for t in action_targets):
        values["STATUS"] = "BLOCKED"
        values["VERDICT"] = "BLOCKED"
        values["BLOCKER_ID"] = "STALE_READY_ACTION"
        values["RISKS"] = "action de dispatch cible un batch qui n'est plus READY"
        values["NEXT"] = "reprendre le prochain item READY depuis la queue runtime"

if not values.get("NEXT_ACTION_UNIQUE", "").strip():
    values["NEXT_ACTION_UNIQUE"] = f"CONTINUE_{role}_RUNTIME_TRUTH"

for k in keys:
    print(f"{k}: {values.get(k, '').strip()}")
PY
  rm -f "$tmp"
}

tmux_target() {
  printf '%s:0.0' "$1"
}

tmux_has_session() {
  tmux has-session -t "$1" >/dev/null 2>&1
}

tmux_pane_current_command() {
  tmux display-message -p -t "$(tmux_target "$1")" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]'
}

tmux_pane_pid() {
  tmux display-message -p -t "$(tmux_target "$1")" "#{pane_pid}" 2>/dev/null | tr -d '[:space:]'
}

tmux_capture() {
  local session="$1"
  local lines="${2:-$TMUX_CAPTURE_LINES}"
  tmux capture-pane -p -J -S "-${lines}" -E -1 -t "$(tmux_target "$session")" 2>/dev/null || true
}

tmux_send_multiline() {
  local session="$1"
  local text="$2"
  local buffer_name="role_runner_$(date +%s)_$$"
  local tmp_path
  tmp_path="$(mktemp)"
  printf '%s' "$text" > "$tmp_path"
  tmux load-buffer -b "$buffer_name" "$tmp_path"
  tmux paste-buffer -d -b "$buffer_name" -t "$(tmux_target "$session")"
  tmux send-keys -t "$(tmux_target "$session")" C-m
  rm -f "$tmp_path"
}

tmux_agent_ready() {
  local session="$1"
  local cmd=""
  local pane_pid=""
  local children=""
  cmd="$(tmux_pane_current_command "$session" || true)"
  if [[ -n "$cmd" ]]; then
    if [[ "$cmd" == *"${AGENT_BIN_NAME,,}"* || "$cmd" == *"codex"* || "$cmd" == "node" ]]; then
      return 0
    fi
  fi
  pane_pid="$(tmux_pane_pid "$session" || true)"
  if [[ "$pane_pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    children="$(pgrep -P "$pane_pid" -af 2>/dev/null || true)"
    if printf '%s\n' "$children" | rg -qi '(codex|openai.*codex|node.*codex)'; then
      return 0
    fi
  fi
  return 1
}

start_role_session() {
  local session="$1"
  local launch_cmd=""
  local agent_cmd=""
  agent_cmd="$(agent_launch_command)"
  tmux start-server >/dev/null 2>&1 || true
  if ! tmux_has_session "$session"; then
    printf -v launch_cmd 'cd %q && unset NO_COLOR && if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi; export COLORTERM="${COLORTERM:-truecolor}"; export FORCE_COLOR="${FORCE_COLOR:-1}"; exec %s' "$ROOT" "$agent_cmd"
    tmux new-session -d -s "$session" "bash -lc $(printf '%q' "$launch_cmd")"
    sleep 1
  fi
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  if ! tmux_agent_ready "$session"; then
    tmux send-keys -t "$(tmux_target "$session")" C-c >/dev/null 2>&1 || true
    sleep 1
    tmux_send_multiline "$session" "$agent_cmd"
  fi
}

ensure_role_session_ready() {
  local role="$1"
  local session=""
  local i=0
  session="$(target_session_name "$role")"
  if [[ -z "$session" ]]; then
    return 1
  fi
  start_role_session "$session"
  for ((i=0; i<TMUX_READY_WAIT_SECONDS; i++)); do
    if tmux_agent_ready "$session"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

restart_role_session() {
  local role="$1"
  local session=""
  session="$(target_session_name "$role")"
  if [[ -z "$session" ]]; then
    return 1
  fi
  if tmux_has_session "$session"; then
    tmux kill-session -t "$session" >/dev/null 2>&1 || true
  fi
  start_role_session "$session"
  return 0
}

health_snapshot_compact() {
  local role=""
  local session=""
  local state=""
  local cmd=""
  local pieces=()
  for role in $(health_roles); do
    session="$(target_session_name "$role")"
    if [[ -z "$session" ]] || ! tmux_has_session "$session"; then
      pieces+=("${role}:DOWN")
      continue
    fi
    if tmux_agent_ready "$session"; then
      pieces+=("${role}:UP")
    else
      cmd="$(tmux_pane_current_command "$session" || true)"
      state="IDLE"
      if [[ -n "$cmd" ]]; then
        state="IDLE(${cmd})"
      fi
      pieces+=("${role}:${state}")
    fi
  done
  (IFS=','; printf 'health_roles=%s' "${pieces[*]}")
}

recover_role_if_needed() {
  local count="$1"
  local restart_out=""
  local health_out=""
  local note="auto_recovery=pending(${count}/${RECOVERY_THRESHOLD})"
  if [[ "$count" -ge "$RECOVERY_THRESHOLD" ]]; then
    if [[ "$CODEX_EXEC_PRIMARY" -eq 1 ]]; then
      clear_codex_session_id
      restart_out="codex_exec_session_reset"
      health_out="codex_exec_mode"
    else
      if restart_role_session "$ROLE"; then
        restart_out="ok"
      else
        restart_out="failed"
      fi
      health_out="$(health_snapshot_compact)"
    fi
    write_fail_count 0
    note="auto_recovery=triggered restart=[${restart_out}] health=[${health_out}]"
  fi
  printf '%s' "$note"
}

# Ensure target session exists, but avoid expensive full restart on every tick.
TARGET_SESSION="$(target_session_name "$ROLE")"
STARTUP_NOTE=""
if [[ "$CODEX_EXEC_PRIMARY" -eq 1 ]]; then
  if [[ "$CODEX_EXEC_RESUME" == "1" ]]; then
    STARTUP_NOTE="startup_mode=codex_exec_resume"
  else
    STARTUP_NOTE="startup_mode=codex_exec_fresh"
  fi
else
  if ! tmux_has_session "$TARGET_SESSION"; then
    START_RC=0
    START_OUT=""
    set +e
    if ensure_role_session_ready "$ROLE"; then
      START_OUT="started"
    else
      START_OUT="failed_to_start_or_ready"
      START_RC=1
    fi
    set -e
    if [[ $START_RC -ne 0 ]]; then
      STARTUP_NOTE="startup_rc=${START_RC}; startup_err=[$(one_line "$START_OUT")]"
    else
      STARTUP_NOTE="startup_rc=0"
    fi
  else
    if ! ensure_role_session_ready "$ROLE"; then
      STARTUP_NOTE="startup_rc=1; startup_err=[session_not_ready]"
    fi
  fi
fi
trace_event "startup session=${TARGET_SESSION} agent=${AGENT_BIN_NAME} primary_channel=${PRIMARY_CHANNEL} startup_note=${STARTUP_NOTE:-none}"

sanitize_tmux_logs() {
  # Optional maintenance pass; disabled by default to keep per-iteration logs intact.
  if [[ "${TMUX_ROLE_AUTO_SANITIZE_LOGS:-0}" != "1" ]]; then
    return 0
  fi
  if [[ -x "scripts/clean_tmux_logs.sh" ]]; then
    bash scripts/clean_tmux_logs.sh --mode compact finance-app/orchestrator-runs >/dev/null 2>&1 || true
  fi
}

build_prompt() {
  local role="$1"
  case "$role" in
    planner)
      cat <<'PROMPT'
ROLE=planner.
Read docs/planning/PRODUCT_VISION.md, docs/planning/epics.md, docs/planning/tasks.md, docs/orchestrator-ops/priority-queue.json, docs/planning/WORKSTATE.md, and finance-app/openclaw-gates.
Do not modify files.
Role mentor: valider que le travail READY/IN_PROGRESS est conforme a la vision produit (forecast-first, prevision API->UI visible, decision en 2-3 clics, cout runtime raisonnable).
Analyser au moins un task READY/IN_PROGRESS par tick et publier un verdict de conformite avec regle explicite.
Mode read-only mentor: utiliser task_update=analysis_only (ou blocked si necessaire), jamais claim/complete/handoff.
Obligatoire: EVIDENCE doit contenir planner_artifact=<preuve_mentor>, task_id=<task>, vision_rule=<regle_verifiee>, conformance=<PASS|WARN|BLOCKED>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      ;;
    analyst)
      cat <<'PROMPT'
ROLE=analyst.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/WORKSTATE.md, and docs/planning/stories.md.
Do not modify files.
Focus: clarifier hypotheses/metier, dependances inter-equipes, et criteres d'acceptance reutilisables par backend/frontend/qa.
Obligatoire: EVIDENCE doit contenir analyst_artifact=<brief_ou_decision> et task_id=<id_stream_ou_task>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      ;;
    backend_engineer)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=backend_engineer.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/tasks.md, and copilot-app/backend.
Execution mode=delivery: prendre un task backend pret et livrer un patch/test concret.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir backend_artifact=<fichier_ou_test>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=backend_engineer.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/tasks.md, and copilot-app/backend.
Mode analyse (read-only): Do not modify files.
Obligatoire: EVIDENCE doit contenir backend_artifact=<fichier_cible_ou_plan>, task_id=<task>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    frontend_engineer)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=frontend_engineer.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/tasks.md, and finance-app.
Execution mode=delivery: prendre un task frontend pret et livrer une modification UI/UX concrete.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir frontend_artifact=<fichier_ou_capture>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=frontend_engineer.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/tasks.md, and finance-app.
Mode analyse (read-only): Do not modify files.
Obligatoire: EVIDENCE doit contenir frontend_artifact=<fichier_cible_ou_plan>, task_id=<task>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    integrator)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=integrator.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/tasks.md, and docs/scrum/sprint-current.md.
Execution mode=delivery: integrer les sorties backend/frontend/infra et verifier les interfaces.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir integrator_artifact=<preuve_integration>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=integrator.
Read docs/orchestrator-ops/priority-queue.json, docs/planning/tasks.md, and docs/scrum/sprint-current.md.
Mode analyse (read-only): Do not modify files.
Obligatoire: EVIDENCE doit contenir integrator_artifact=<plan_integration>, task_id=<task>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    data_analyst)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=data_analyst.
Read docs/orchestrator-ops/priority-queue.json, data, and docs/planning/tasks.md.
Execution mode=delivery: produire une preuve data exploitable (requete, metrique, controle qualite) en support des equipes.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir data_artifact=<requete_ou_resultat>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=data_analyst.
Read docs/orchestrator-ops/priority-queue.json, data, and docs/planning/tasks.md.
Mode analyse (read-only): Do not modify files.
Obligatoire: EVIDENCE doit contenir data_artifact=<analyse_ou_metric>, task_id=<task>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    infra_engineer)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=infra_engineer.
Read docs/orchestrator-ops/priority-queue.json, docs/ops, and scripts.
Execution mode=delivery: appliquer une amelioration infra/CI/observabilite qui accelere la livraison.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir infra_artifact=<fichier_ou_check_infra>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=infra_engineer.
Read docs/orchestrator-ops/priority-queue.json, docs/ops, and scripts.
Mode analyse (read-only): Do not modify files.
Obligatoire: EVIDENCE doit contenir infra_artifact=<plan_infra>, task_id=<task>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    dev)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=dev.
Read docs/planning/tasks.md, docs/planning/stories.md, and docs/orchestrator-ops/priority-queue.json.
Read workboard lane context first: python3 scripts/parallel_workstream.py context --role dev --limit 5.
WORKDIR obligatoire pour toute commande: /home/venom/analyse-financiere (alias OK: /home/venom/shared/analyse-financiere).
Execution mode=delivery: exécute une boucle complète claim -> patch minimal -> test ciblé -> complete/handoff.
Si une tâche dev est READY: claim explicite via scripts/parallel_workstream.py claim --role dev avant patch.
Si une tâche dev est IN_PROGRESS: reprendre/fermer cette tâche avant toute autre action.
Si aucune tâche dev READY/IN_PROGRESS n'existe: ne pas inventer de travail, utiliser task_update=none_no_ready.
Avant tout blocker read-only/permission, exécuter un probe concret (ex: test -w docs/orchestrator-ops/parallel-workstreams.json) et inclure cmd_err_excerpt exact.
Ne pas recycler un ancien blocker read-only sans preuve fraîche du tick courant.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir dev_artifact=<fichier_modifie_ou_patch>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Si task_update=blocked avec un motif permission/read-only, ajouter cmd_err_excerpt=<stderr_reel>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=dev.
Read docs/planning/tasks.md, docs/planning/stories.md, and docs/orchestrator-ops/priority-queue.json.
Mode analyse (read-only): Do not modify files.
Si queue_has_ready=1 mais workboard_role_has_work=0 et workboard_role_has_in_progress=0: utiliser task_update=none_no_ready.
Obligatoire: EVIDENCE doit contenir dev_artifact=<fichier_cible_ou_patch_plan>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    tester)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=tester.
Read copilot-app/backend/tests, docs/planning/tasks.md, and docs/orchestrator-ops/priority-queue.json.
Execution mode=delivery: exécute réellement les tests minimaux liés à l'item READY.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir tester_artifact=<suite_test_ou_commande>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=tester.
Read copilot-app/backend/tests, docs/planning/tasks.md, and docs/orchestrator-ops/priority-queue.json.
Mode analyse (read-only): Do not modify files.
Obligatoire: EVIDENCE doit contenir tester_artifact=<suite_test_ou_commande>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    qa)
      if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
      cat <<'PROMPT'
ROLE=qa.
Read finance-app/openclaw-gates, docs/orchestrator-ops/priority-queue.json, docs/orchestrator-ops/parallel-workstreams.json, and docs/scrum/sprint-current.md.
Read workboard lane context first: python3 scripts/parallel_workstream.py context --role qa --limit 5.
Execution mode=delivery: vérifie la cohérence gate/queue/workboard et livre un verdict actionnable.
Si aucune tâche QA n'est READY/IN_PROGRESS: utiliser task_update=none_no_ready et expliciter les deps restantes (ex: depends_on) dans RISKS/NEXT.
Commandes shell via scripts/exec_safe.sh.
Obligatoire: EVIDENCE doit contenir qa_artifact=<gate_ou_preuve_validation|doc_fix>, stream_id=<stream>, task_id=<task>, cmd=<commande_executee_ou_SKIP(raison)>, tests_run=<suite:PASS|FAIL|SKIP(raison)>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      else
      cat <<'PROMPT'
ROLE=qa.
Read finance-app/openclaw-gates, docs/orchestrator-ops/priority-queue.json, docs/orchestrator-ops/parallel-workstreams.json, and docs/scrum/sprint-current.md.
Read workboard lane context first: python3 scripts/parallel_workstream.py context --role qa --limit 5.
Mode analyse (read-only): Do not modify files.
Validate gate coherence and blockers.
Obligatoire: EVIDENCE doit contenir qa_artifact=<gate_ou_preuve_validation>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      fi
      ;;
    architect)
      cat <<'PROMPT'
ROLE=architect.
Read docs/planning/epics.md, docs/planning/stories.md, docs/planning/tasks.md, docs/ops/API_ENDPOINT_BEST_PRACTICES.md, docs/ops/REUSE_MODULES_CATALOG.md, and docs/orchestrator-ops/priority-queue.json.
Do not modify files.
Validate architecture best-practices compliance for the current delivery scope.
If queue_has_ready=1 or workboard_role_has_in_progress=1, anchor review to that scope and include stream_id/task_id.
Obligatoire: EVIDENCE doit contenir architect_artifact=<decision_ou_contrainte_archi>; arch_rule=<api_contract|forecast_contract|schema_stability|reusability|observability|security>; review_scope=<stream_task_ou_composant>; conformance=<PASS|WARN|BLOCKED>; violations=<none_ou_liste>; task_update=<analysis_only|blocked|none_no_ready|none_no_signal>; lock_check=ok.
If conformance=BLOCKED, STATUS/VERDICT must be BLOCKED with a non-NONE BLOCKER_ID.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      ;;
    po)
      cat <<'PROMPT'
ROLE=po.
Read docs/planning/mvp-plan.md, docs/planning/epics.md, and docs/orchestrator-ops/priority-queue.json.
Do not modify files.
Verify backlog priority and scope alignment, then propose one PO decision.
Obligatoire: EVIDENCE doit contenir po_artifact=<decision_backlog_ou_scope>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      ;;
    scrum_master)
      cat <<'PROMPT'
ROLE=scrum_master.
Read docs/scrum/sprint-current.md, docs/orchestrator-ops/priority-queue.json, and docs/planning/WORKSTATE.md.
Do not modify files.
Check WIP, blockers, and sprint hygiene, then propose one next scrum action.
Obligatoire: EVIDENCE doit contenir scrum_artifact=<action_wip_ou_blocage>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      ;;
    clawsentinel)
      cat <<'PROMPT'
ROLE=clawsentinel.
Read docs/ops/ADMIN_TEAM_CHAT.md, docs/ops/ADMIN_TEAM_ITERATIONS.md, docs/orchestrator-ops/agent-watchdog.md, and docs/orchestrator-ops/priority-queue.json.
Do not modify files.
As safety/quality owner, provide one concrete anti-drift or reliability action for the current READY flow.
Obligatoire: EVIDENCE doit contenir sentinel_artifact=<controle_ou_action_antidrift>.
Return at most 10 lines with keys:
STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
If nothing changed, set DELTA: NO_DELTA.
PROMPT
      ;;
  esac
}

required_artifact_marker_for_role() {
  case "$1" in
    planner) echo "PLANNER_ARTIFACT=" ;;
    analyst) echo "ANALYST_ARTIFACT=" ;;
    dev) echo "DEV_ARTIFACT=" ;;
    backend_engineer) echo "BACKEND_ARTIFACT=" ;;
    frontend_engineer) echo "FRONTEND_ARTIFACT=" ;;
    integrator) echo "INTEGRATOR_ARTIFACT=" ;;
    data_analyst) echo "DATA_ARTIFACT=" ;;
    infra_engineer) echo "INFRA_ARTIFACT=" ;;
    tester) echo "TESTER_ARTIFACT=" ;;
    qa) echo "QA_ARTIFACT=" ;;
    architect) echo "ARCHITECT_ARTIFACT=" ;;
    po) echo "PO_ARTIFACT=" ;;
    scrum_master) echo "SCRUM_ARTIFACT=" ;;
    clawsentinel) echo "SENTINEL_ARTIFACT=" ;;
    *) echo "ROLE_ARTIFACT=" ;;
  esac
}

PROMPT_TEXT="$(build_prompt "$ROLE")"
SYSTEM_PROMPT="Ignore l'historique non pertinent. Réponds uniquement en français avec exactement 8 lignes dans cet ordre: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE. Une seule valeur par ligne et aucun texte hors contrat. Appuie-toi sur les états fournis dans RUNTIME_CONTEXT (queue_states, queue_has_ready, workboard_role_has_work, workboard_role_has_in_progress, queue_version, workboard_version, now_iso, agent_memory, self_last_contract, peer_contracts, workboard_context, team_chat_tail, team_iteration_tail). Si queue_has_ready=1, DELTA ne doit pas être NO_DELTA et NEXT_ACTION_UNIQUE doit cibler un item READY actuel. Si queue_has_ready=0 mais workboard_role_has_in_progress=1, tu dois reprendre/fermer cette tache IN_PROGRESS (pas analysis_only). Tu dois reprendre le travail interrompu s'il existe un self_last_contract récent, sauf si ce contrat évoque un blocker read-only/permission non prouvé pour ce tick. EVIDENCE doit etre en format kv key=value;key2=value2. EVIDENCE doit inclure task_update=<claim|complete|handoff|blocked|analysis_only|none_no_ready|none_no_signal> et lock_check=ok. Quand queue_has_ready=1 ou workboard_role_has_work=1, ajoute stream_id=<...> et task_id=<...>. Si task_update=claim|complete|handoff, stream_id/task_id sont obligatoires. Si task_update=handoff, ajoute handoff_to=<role> et handoff_ref=<id|pending>. Si task_update=complete, ajoute cmd=<...|SKIP(raison)> et tests_run=<...|SKIP(raison)>. NEXT doit nommer explicitement le owner suivant (format owner=<role>; action=<...>). Si STATUS=BLOCKED alors BLOCKER_ID ne doit jamais etre NONE. Un blocker read-only/permission doit inclure cmd_err_excerpt exact du tick courant. WORKDIR attendu: /home/venom/analyse-financiere (alias OK: /home/venom/shared/analyse-financiere). N'invente pas de blocker historique non présent dans queue_states."
if [[ "$ROLE_ALLOW_FILE_EDITS_EFFECTIVE" -eq 1 ]]; then
  SYSTEM_PROMPT="${SYSTEM_PROMPT} Tu es en mode delivery: exécute réellement les commandes nécessaires (via scripts/exec_safe.sh), évite les plans fictifs, mets à jour les tâches/handoffs via scripts/parallel_workstream.py, et fournis des preuves concrètes."
else
  SYSTEM_PROMPT="${SYSTEM_PROMPT} Tu es en mode analyse: n'édite pas de fichiers et ne déclenche pas d'actions externes. Si workboard_role_has_work=0 et workboard_role_has_in_progress=0, utilise task_update=none_no_ready."
fi

ORCHESTRATION_SHARED_PROMPT="$(cat <<'PROMPT'
PROTOCOLE_ORCHESTRATION_COMMUN:
- Source unique des tâches: docs/planning/tasks.md (pas de création de tâches dans docs Scrum/backlog).
- Co-édition: claim d'abord (scripts/parallel_workstream.py claim --role <role>), patch minimal sur la section claimée, collision => merge explicite (jamais écraser).
- Avant édition cross-section: publier un INTENT dans docs/ops/ADMIN_TEAM_CHAT.md.
- Handoffs: ack/close prioritaire si handoffs_to_ids!=none, puis documenter handoff_to/handoff_ref dans EVIDENCE.
- Communication inter-rôles: NEXT doit avoir owner explicite (owner=<role>; action=<...>) pour éviter les ambiguïtés.
- Si aucun slot rôle READY/IN_PROGRESS: task_update=none_no_ready (pas de faux blocker).
PROMPT
)"

build_runtime_context() {
  local ready_items=""
  local blocked_items=""
  local queue_states=""
  local queue_has_ready="0"
  local queue_version=""
  local workboard_version=""
  local ready_next_actions=""
  local workstate_hint=""
  local parallel_hint=""
  local workboard_role_has_work=""
  local workboard_role_has_in_progress=""
  local agent_memory_hint=""
  local self_last_contract_hint=""
  local peer_contracts_hint_text=""
  local workboard_context=""
  local team_chat_tail=""
  local team_iteration_tail=""
  local trace_tail=""
  local now_iso=""
  now_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ -f "docs/orchestrator-ops/priority-queue.json" ]]; then
    ready_items="$(jq -r '.items[]? | select(.state=="READY") | "\(.id):\(.title)"' docs/orchestrator-ops/priority-queue.json 2>/dev/null | head -n 3 | tr '\n' '; ')"
    blocked_items="$(jq -r '.items[]? | select(.state=="BLOCKED") | "\(.id):\(.blocker_id // "NONE")"' docs/orchestrator-ops/priority-queue.json 2>/dev/null | head -n 3 | tr '\n' '; ')"
    queue_states="$(jq -r '.items[]? | "\(.id)=\(.state)"' docs/orchestrator-ops/priority-queue.json 2>/dev/null | head -n 8 | tr '\n' '; ')"
    ready_next_actions="$(jq -r '.items[]? | select(.state=="READY") | "\(.id):\(.next_action // "NONE")"' docs/orchestrator-ops/priority-queue.json 2>/dev/null | head -n 5 | tr '\n' '; ')"
    queue_has_ready="$(jq -r '[.items[]? | select(.state=="READY")] | if length>0 then "1" else "0" end' docs/orchestrator-ops/priority-queue.json 2>/dev/null || printf '0')"
  fi
  queue_version="${RUNTIME_QUEUE_VERSION:-queue_unknown}"
  workboard_version="${RUNTIME_WORKBOARD_VERSION:-workboard_unknown}"
  if [[ -f "docs/planning/WORKSTATE.md" ]]; then
    workstate_hint="$(tail -n 20 docs/planning/WORKSTATE.md 2>/dev/null | tr '\n' ' ' | tr -s ' ' | cut -c1-320)"
  fi
  if [[ -x "scripts/parallel_workstream.py" ]]; then
    parallel_hint="$(python3 scripts/parallel_workstream.py status --role "$ROLE" --compact --limit 3 2>/dev/null | tr '\n' '; ' | tr -s ' ' | cut -c1-380)"
  fi
  workboard_role_has_work="${RUNTIME_WORKBOARD_ROLE_HAS_WORK:-0}"
  workboard_role_has_in_progress="${RUNTIME_WORKBOARD_ROLE_HAS_IN_PROGRESS:-0}"
  agent_memory_hint="$(compact_file_tail "${ROLE_MEMORY_DIR}/${ROLE}.md" 24 420)"
  self_last_contract_hint="$(read_last_contract_hint "$LAST_CONTRACT_FILE" "self" | cut -c1-420)"
  peer_contracts_hint_text="$(peer_contracts_hint)"
  workboard_context="$(workboard_context_hint)"
  team_chat_tail="$(compact_file_tail "$TEAM_CHAT_FILE" 10 340)"
  team_iteration_tail="$(compact_file_tail "$TEAM_ITER_FILE" 8 260)"
  trace_tail="$(compact_file_tail "$TRACE_FILE" 8 280)"

  printf 'RUNTIME_CONTEXT: now_iso=%s | queue_states=%s | queue_has_ready=%s | queue_version=%s | workboard_version=%s | ready_items=%s | ready_next_actions=%s | blocked_items=%s | workstate_hint=%s | parallel_hint=%s | workboard_role_has_work=%s | workboard_role_has_in_progress=%s | agent_memory=%s | self_last_contract=%s | peer_contracts=%s | workboard_context=%s | team_chat_tail=%s | team_iteration_tail=%s | trace_tail=%s | execution_rules=respect_run_lock,update_tasks,ack_handoffs' \
    "${now_iso:-unknown}" \
    "${queue_states:-none}" \
    "${queue_has_ready:-0}" \
    "${queue_version:-queue_unknown}" \
    "${workboard_version:-workboard_unknown}" \
    "${ready_items:-none}" \
    "${ready_next_actions:-none}" \
    "${blocked_items:-none}" \
    "${workstate_hint:-none}" \
    "${parallel_hint:-none}" \
    "${workboard_role_has_work:-0}" \
    "${workboard_role_has_in_progress:-0}" \
    "${agent_memory_hint:-none}" \
    "${self_last_contract_hint:-none}" \
    "${peer_contracts_hint_text:-none}" \
    "${workboard_context:-none}" \
    "${team_chat_tail:-none}" \
    "${team_iteration_tail:-none}" \
    "${trace_tail:-none}"
}
RUNTIME_CONTEXT="$(build_runtime_context)"

capture_has_contract() {
  local text="$1"
  printf '%s\n' "$text" | rg -qi 'status\s*[:=]' \
    && printf '%s\n' "$text" | rg -qi 'delta\s*[:=]' \
    && printf '%s\n' "$text" | rg -qi 'verdict\s*[:=]' \
    && printf '%s\n' "$text" | rg -qi 'blocker_id\s*[:=]' \
    && printf '%s\n' "$text" | rg -qi 'next_action_unique\s*[:=]'
}

build_dispatch_prompt() {
  local prompt_text="$1"
  local tick="$2"
  cat <<EOF
${SYSTEM_PROMPT}
${ORCHESTRATION_SHARED_PROMPT}
${RUNTIME_CONTEXT}

${prompt_text}

Freshness constraint: NEXT_ACTION_UNIQUE must end with _${tick}
EOF
}

extract_codex_exec_thread_id() {
  local tmp=""
  tmp="$(mktemp)"
  cat > "$tmp"
  python3 - "$tmp" <<'PY'
import json
import re
import sys
from pathlib import Path

payload_path = Path(sys.argv[1])
text = payload_path.read_text(encoding="utf-8", errors="ignore")
thread_id = ""
for raw in text.splitlines():
    line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
    if not line:
        continue
    start = line.find("{")
    end = line.rfind("}")
    if start < 0 or end < start:
        continue
    line = line[start : end + 1]
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get("type") == "thread.started":
        tid = obj.get("thread_id") or ""
        if tid:
            thread_id = tid
if thread_id:
    print(thread_id)
PY
  rm -f "$tmp"
}

extract_codex_exec_message() {
  local tmp=""
  tmp="$(mktemp)"
  cat > "$tmp"
  python3 - "$tmp" <<'PY'
import json
import re
import sys
from pathlib import Path

payload_path = Path(sys.argv[1])
text = payload_path.read_text(encoding="utf-8", errors="ignore")
msg = ""
for raw in text.splitlines():
    line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
    if not line:
        continue
    start = line.find("{")
    end = line.rfind("}")
    if start < 0 or end < start:
        continue
    line = line[start : end + 1]
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get("type") != "item.completed":
        continue
    item = obj.get("item") or {}
    if item.get("type") == "agent_message":
        text = item.get("text") or ""
        if text:
            msg = text
if msg:
    print(msg)
PY
  rm -f "$tmp"
}

codex_exec_prompt_once() {
  local timeout_seconds="$1"
  local prompt_text="$2"
  local tick="$3"
  local prompt_payload=""
  local session_id=""
  local allow_resume=0
  local output=""
  local rc=0
  local sid_new=""
  local msg=""
  local used_resume=0
  local msg_file=""
  local -a codex_cmd=()

  prompt_payload="$(build_dispatch_prompt "$prompt_text" "$tick")"
  while IFS= read -r token; do
    [[ -z "$token" ]] && continue
    codex_cmd+=("$token")
  done < <(build_codex_global_args)

  if [[ "$CODEX_EXEC_RESUME" == "1" ]]; then
    allow_resume=1
    session_id="$(read_codex_session_id)"
  else
    clear_codex_session_id
  fi

  msg_file="$(mktemp)"
  if [[ "$allow_resume" -eq 1 && -n "$session_id" ]]; then
    used_resume=1
    set +e
    output="$(timeout "${timeout_seconds}" codex "${codex_cmd[@]}" exec resume "$session_id" --model "$CODEX_EXEC_MODEL" --json "$prompt_payload" 2>&1)"
    rc=$?
    set -e
    if [[ $rc -ne 0 ]] && printf '%s\n' "$output" | rg -qi 'session.*not found|unknown session|invalid session|no such session'; then
      clear_codex_session_id
      session_id=""
    fi
    # Resume can timeout or fail without producing a usable message; fallback to a fresh thread.
    if [[ $rc -ne 0 ]]; then
      clear_codex_session_id
      session_id=""
    fi
  fi

  if [[ -z "$session_id" ]]; then
    set +e
    output="$(timeout "${timeout_seconds}" codex "${codex_cmd[@]}" exec --model "$CODEX_EXEC_MODEL" --output-last-message "$msg_file" --json "$prompt_payload" 2>&1)"
    rc=$?
    set -e
  fi

  sid_new=""
  if [[ "$allow_resume" -eq 1 ]]; then
    sid_new="$(printf '%s\n' "$output" | extract_codex_exec_thread_id || true)"
  fi
  if [[ "$allow_resume" -eq 1 && -n "$sid_new" ]]; then
    write_codex_session_id "$sid_new"
  fi

  if [[ -s "$msg_file" ]]; then
    msg="$(cat "$msg_file" 2>/dev/null || true)"
  fi
  if [[ -z "$msg" ]]; then
    msg="$(printf '%s\n' "$output" | extract_codex_exec_message || true)"
  fi
  if [[ "$allow_resume" -eq 1 && $rc -eq 0 && -z "$msg" && "$used_resume" -eq 1 ]]; then
    # Resume can occasionally return an empty content turn; retry once on a fresh thread.
    clear_codex_session_id
    set +e
    rm -f "$msg_file"
    msg_file="$(mktemp)"
    output="$(timeout "${timeout_seconds}" codex "${codex_cmd[@]}" exec --model "$CODEX_EXEC_MODEL" --output-last-message "$msg_file" --json "$prompt_payload" 2>&1)"
    rc=$?
    set -e
    sid_new="$(printf '%s\n' "$output" | extract_codex_exec_thread_id || true)"
    if [[ -n "$sid_new" ]]; then
      write_codex_session_id "$sid_new"
    fi
    if [[ -s "$msg_file" ]]; then
      msg="$(cat "$msg_file" 2>/dev/null || true)"
    fi
    if [[ -z "$msg" ]]; then
      msg="$(printf '%s\n' "$output" | extract_codex_exec_message || true)"
    fi
  fi
  rm -f "$msg_file"

  if [[ $rc -ne 0 ]]; then
    printf '%s\n' "$output"
    return $rc
  fi

  if [[ -n "$msg" ]]; then
    printf '%s\n' "$msg"
    return 0
  fi

  printf '%s\n' "$output" > "${STATE_DIR}/${ROLE}.codex_exec_last_raw.jsonl"
  printf '%s\n' "$output"
  return 65
}

prompt_once() {
  local timeout_seconds="$1"
  local prompt_text="$2"
  local tick="$3"
  local channel="${4:-${PRIMARY_CHANNEL:-tmux}}"
  local prompt_payload=""
  local deadline=0
  local now=0
  local capture=""
  local capture_sig=""
  local last_capture_sig=""
  local last_progress_at=0
  local stalled_for=0

  if [[ "$channel" == "codex_exec" ]]; then
    codex_exec_prompt_once "$timeout_seconds" "$prompt_text" "$tick"
    return $?
  fi

  if ! ensure_role_session_ready "$ROLE"; then
    printf 'session_not_ready role=%s session=%s\n' "$ROLE" "$TARGET_SESSION"
    return 43
  fi

  tmux send-keys -t "$(tmux_target "$TARGET_SESSION")" C-l >/dev/null 2>&1 || true
  tmux clear-history -t "$(tmux_target "$TARGET_SESSION")" >/dev/null 2>&1 || true
  prompt_payload="$(build_dispatch_prompt "$prompt_text" "$tick")"
  tmux_send_multiline "$TARGET_SESSION" "$prompt_payload"

  deadline=$(( $(date +%s) + timeout_seconds ))
  last_progress_at="$(date +%s)"
  while true; do
    capture="$(tmux_capture "$TARGET_SESSION" "$TMUX_CAPTURE_LINES")"
    if [[ -n "$capture" ]] && capture_has_contract "$capture"; then
      printf '%s\n' "$capture"
      return 0
    fi
    now="$(date +%s)"
    capture_sig="${#capture}:$(printf '%s\n' "$capture" | tail -n 4 | tr '\n' ' ' | tr -s ' ' | cut -c1-180)"
    if [[ "$capture_sig" != "$last_capture_sig" ]]; then
      last_capture_sig="$capture_sig"
      last_progress_at="$now"
    fi
    if [[ "$TMUX_STALL_ABORT_SECONDS" -gt 0 ]]; then
      stalled_for="$(( now - last_progress_at ))"
      if [[ "$stalled_for" -ge "$TMUX_STALL_ABORT_SECONDS" ]]; then
        trace_event "prompt_stall_abort tick=${tick} channel=${channel} stalled_for=${stalled_for}s bytes=${#capture}"
        printf '%s\n' "$capture"
        return 124
      fi
    fi
    if [[ "$now" -ge "$deadline" ]]; then
      printf '%s\n' "$capture"
      return 124
    fi
    sleep "$TMUX_POLL_INTERVAL_SECONDS"
  done
}

normalize_output() {
  local tmp=""
  tmp="$(mktemp)"
  cat > "$tmp"
  python3 - "$ROLE" "$tmp" <<'PY'
import re
import sys
from pathlib import Path

role = sys.argv[1]
payload_path = Path(sys.argv[2])
lines = payload_path.read_text(encoding="utf-8", errors="ignore").splitlines()
text_all = "\n".join(lines)
keys = [
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
]
values = {k: "" for k in keys}
defaults_partial = {
    "STATUS": "IN_PROGRESS",
    "DELTA": "NO_DELTA",
    "EVIDENCE": "Réponse tmux partielle; champs manquants complétés automatiquement.",
    "RISKS": f"signal incomplet pour {role}, à reconfirmer au prochain tick",
    "NEXT": "poursuivre le prochain cycle avec même rôle",
    "VERDICT": "GO_WITH_CAUTION",
    "BLOCKER_ID": "NONE",
    "NEXT_ACTION_UNIQUE": f"CONTINUE_{role}_TMUX_ROLE_RUNNER",
}

key_token_pat = re.compile(
    r"(status|delta|evidence|risks|next|verdict|blocker_id|next_action_unique)\s*[:：=]",
    re.IGNORECASE,
)

# Reject idle Codex banner/prompt replies that are not role outputs.
if not key_token_pat.search(text_all):
    if re.search(
        r"OpenAI Codex|100% context left|/model to change|Tip:|directory:",
        text_all,
        re.IGNORECASE,
    ):
        sys.exit(2)

for raw in lines:
    line = raw.strip()
    if not line:
        continue
    line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
    matches = list(key_token_pat.finditer(line))
    if not matches:
        continue
    for idx, m in enumerate(matches):
        key = m.group(1).upper()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
        val = line[start:end].strip(" ,;|")
        if val and not values.get(key):
            values[key] = val

found = sum(1 for v in values.values() if v)
if found == 0:
    text = "\n".join(lines)
    inline_pat = re.compile(
        r"(status|delta|evidence|risks|next|verdict|blocker_id|next_action_unique)\s*[:：=]\s*([^,\n]+)",
        re.IGNORECASE,
    )
    for m in inline_pat.finditer(text):
        key = m.group(1).upper()
        val = m.group(2).strip()
        if val and not values.get(key):
            values[key] = val
    found = sum(1 for v in values.values() if v)
if found == 0:
    sys.exit(2)

required = ("STATUS", "DELTA", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE")
if any(not values.get(k) for k in required):
    sys.exit(2)

for k in keys:
    v = values[k] if values[k] else defaults_partial[k]
    print(f"{k}: {v}")
PY
  rm -f "$tmp"
}

response_has_tick() {
  local payload="$1"
  local tick="$2"
  local channel="${3:-${PRIMARY_CHANNEL:-tmux}}"
  if [[ "$channel" == "codex_exec" ]]; then
    return 0
  fi
  printf '%s\n' "$payload" | rg -q "^NEXT_ACTION_UNIQUE:[[:space:]].*_${tick}[[:space:]]*$"
}

RAW_OUTPUT=""
STRUCTURED=""
RC_PRIMARY=0
PRIMARY_TICK="P$(date +%s)_$RANDOM"
trace_event "primary_prompt_begin tick=${PRIMARY_TICK} timeout=${PROMPT_TIMEOUT_SECONDS}s channel=${PRIMARY_CHANNEL}"
set +e
RAW_OUTPUT="$(prompt_once "$PROMPT_TIMEOUT_SECONDS" "$PROMPT_TEXT" "$PRIMARY_TICK" "$PRIMARY_CHANNEL" 2>&1)"
RC_PRIMARY=$?
set -e
trace_event "primary_prompt_end tick=${PRIMARY_TICK} rc=${RC_PRIMARY} bytes=${#RAW_OUTPUT}"
if [[ $RC_PRIMARY -eq 0 ]]; then
  if STRUCTURED="$(printf "%s\n" "$RAW_OUTPUT" | normalize_output)"; then
    if response_has_tick "$STRUCTURED" "$PRIMARY_TICK" "$PRIMARY_CHANNEL"; then
      trace_event "primary_structured_ok tick=${PRIMARY_TICK}"
      write_fail_count 0
      STRUCTURED="$(printf "%s\n" "$STRUCTURED" | reconcile_runtime_truth)"
      STRUCTURED="$(apply_no_delta_gate "$STRUCTURED" "primary_structured")"
      STRUCTURED="$(printf "%s\n" "$STRUCTURED" | enforce_role_delivery_contract "primary_structured")"
      sanitize_tmux_logs
      persist_last_contract "$STRUCTURED"
      trace_event "final_output source=primary"
      printf "%s\n" "$STRUCTURED"
      exit 0
    fi
    RC_PRIMARY=65
    RAW_OUTPUT="${RAW_OUTPUT}"$'\n'"tick_mismatch=${PRIMARY_TICK}"
  fi
fi

REQUIRED_ARTIFACT_MARKER="$(required_artifact_marker_for_role "$ROLE")"
RETRY_PROMPT="$(cat <<EOF
${PROMPT_TEXT}
Rappel critique:
- Réponds avec exactement 8 lignes dans cet ordre: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
- Une seule valeur utile par ligne, sans commentaire ni texte hors contrat.
- Obligatoire: EVIDENCE doit contenir ${REQUIRED_ARTIFACT_MARKER}<valeur_concrete>.
- Obligatoire: EVIDENCE doit contenir task_update=<...> et lock_check=ok.
- Si queue_has_ready=1 ou workboard_role_has_work=1: inclure stream_id=<...> et task_id=<...>.
- Si task_update=complete: inclure cmd=<...|SKIP(raison)> et tests_run=<...|SKIP(raison)>.
- Interdit: sortie générique READY/DISPATCH sans preuve explicite du rôle.
EOF
)"

RAW_RETRY=""
RC_RETRY=0
RETRY_MODE="$PRIMARY_CHANNEL"
RETRY_CHANNEL="$PRIMARY_CHANNEL"
if [[ $RC_PRIMARY -eq 124 && "$SKIP_RETRY_ON_TIMEOUT" -eq 1 && "$PRIMARY_CHANNEL" == "tmux" ]]; then
  RETRY_MODE="tmux_on_timeout"
  RETRY_CHANNEL="tmux"
fi
RETRY_TICK="R$(date +%s)_$RANDOM"
trace_event "retry_prompt_begin tick=${RETRY_TICK} timeout=${RETRY_PROMPT_TIMEOUT_SECONDS}s channel=${RETRY_CHANNEL} mode=${RETRY_MODE}"
set +e
RAW_RETRY="$(prompt_once "$RETRY_PROMPT_TIMEOUT_SECONDS" "$RETRY_PROMPT" "$RETRY_TICK" "$RETRY_CHANNEL" 2>&1)"
RC_RETRY=$?
set -e
trace_event "retry_prompt_end tick=${RETRY_TICK} rc=${RC_RETRY} bytes=${#RAW_RETRY}"
if [[ $RC_RETRY -eq 0 ]]; then
  if STRUCTURED="$(printf "%s\n" "$RAW_RETRY" | normalize_output)"; then
    if response_has_tick "$STRUCTURED" "$RETRY_TICK" "$RETRY_CHANNEL"; then
      trace_event "retry_structured_ok tick=${RETRY_TICK}"
      write_fail_count 0
      STRUCTURED="$(printf "%s\n" "$STRUCTURED" | reconcile_runtime_truth)"
      STRUCTURED="$(apply_no_delta_gate "$STRUCTURED" "retry_structured")"
      STRUCTURED="$(printf "%s\n" "$STRUCTURED" | enforce_role_delivery_contract "retry_structured")"
      sanitize_tmux_logs
      persist_last_contract "$STRUCTURED"
      trace_event "final_output source=retry"
      printf "%s\n" "$STRUCTURED"
      exit 0
    fi
    RC_RETRY=65
    RAW_RETRY="${RAW_RETRY}"$'\n'"tick_mismatch=${RETRY_TICK}"
  fi
fi

RAW_CODEX_FALLBACK=""
RC_CODEX_FALLBACK=-1
CODEX_FALLBACK_TIMEOUT=0
if [[ "$CODEX_EXEC_AVAILABLE" -eq 1 && "$PRIMARY_CHANNEL" == "tmux" ]]; then
  OUTPUT_CHANNEL_LABEL="tmux+codex_exec_fallback"
  CODEX_FALLBACK_TIMEOUT="$PROMPT_TIMEOUT_SECONDS"
  if [[ "$CODEX_FALLBACK_TIMEOUT" -lt "$RETRY_PROMPT_TIMEOUT_SECONDS" ]]; then
    CODEX_FALLBACK_TIMEOUT="$RETRY_PROMPT_TIMEOUT_SECONDS"
  fi
  # Codex exec JSON mode can stream for longer than tmux scrape windows.
  # Keep a higher floor to avoid false timeout fallbacks.
  if [[ "$CODEX_FALLBACK_TIMEOUT" -lt 90 ]]; then
    CODEX_FALLBACK_TIMEOUT=90
  fi
  CODEX_TICK="C$(date +%s)_$RANDOM"
  trace_event "codex_fallback_begin tick=${CODEX_TICK} timeout=${CODEX_FALLBACK_TIMEOUT}s"
  set +e
  RAW_CODEX_FALLBACK="$(prompt_once "$CODEX_FALLBACK_TIMEOUT" "$RETRY_PROMPT" "$CODEX_TICK" "codex_exec" 2>&1)"
  RC_CODEX_FALLBACK=$?
  set -e
  trace_event "codex_fallback_end tick=${CODEX_TICK} rc=${RC_CODEX_FALLBACK} bytes=${#RAW_CODEX_FALLBACK}"
  if [[ $RC_CODEX_FALLBACK -eq 0 ]]; then
    if STRUCTURED="$(printf "%s\n" "$RAW_CODEX_FALLBACK" | normalize_output)"; then
      if response_has_tick "$STRUCTURED" "$CODEX_TICK" "codex_exec"; then
        trace_event "codex_fallback_structured_ok tick=${CODEX_TICK}"
        write_fail_count 0
        RETRY_MODE="codex_exec_fallback"
        STRUCTURED="$(printf "%s\n" "$STRUCTURED" | reconcile_runtime_truth)"
        STRUCTURED="$(apply_no_delta_gate "$STRUCTURED" "codex_exec_fallback")"
        STRUCTURED="$(printf "%s\n" "$STRUCTURED" | enforce_role_delivery_contract "codex_exec_fallback")"
        sanitize_tmux_logs
        persist_last_contract "$STRUCTURED"
        trace_event "final_output source=codex_fallback"
        printf "%s\n" "$STRUCTURED"
        exit 0
      fi
      RC_CODEX_FALLBACK=65
      RAW_CODEX_FALLBACK="${RAW_CODEX_FALLBACK}"$'\n'"tick_mismatch=${CODEX_TICK}"
    fi
  fi
fi

PRIMARY_PREVIEW="$(sanitize_evidence_fragment "$(one_line "${RAW_OUTPUT:-}")")"
RETRY_PREVIEW="$(sanitize_evidence_fragment "$(one_line "${RAW_RETRY:-}")")"
CODEX_PREVIEW="$(sanitize_evidence_fragment "$(one_line "${RAW_CODEX_FALLBACK:-}")")"
STARTUP_NOTE_SAFE="$(sanitize_evidence_fragment "${STARTUP_NOTE:-startup_skipped=1}")"

FALLBACK_SOURCE=""
FALLBACK_NEXT=""
FALLBACK_ACTION=""
case "$ROLE" in
  planner)
    FALLBACK_SOURCE="docs/orchestrator-ops/priority-queue.json"
    FALLBACK_NEXT="vérifier READY/BLOCKED puis prioriser une action unique"
    FALLBACK_ACTION="CONTINUE_PLANNER_FROM_PRIORITY_QUEUE"
    ;;
  analyst)
    FALLBACK_SOURCE="docs/planning/stories.md"
    FALLBACK_NEXT="maintenir un brief d'analyse actionnable pour les equipes parallelisees"
    FALLBACK_ACTION="CONTINUE_ANALYST_FROM_STORIES"
    ;;
  dev)
    FALLBACK_SOURCE="docs/planning/tasks.md"
    FALLBACK_NEXT="préparer l'action dev exécutable du prochain item READY"
    FALLBACK_ACTION="CONTINUE_DEV_FROM_TASKS"
    ;;
  backend_engineer)
    FALLBACK_SOURCE="docs/planning/tasks.md"
    FALLBACK_NEXT="maintenir la prochaine action backend executable avec preuve attendue"
    FALLBACK_ACTION="CONTINUE_BACKEND_FROM_TASKS"
    ;;
  frontend_engineer)
    FALLBACK_SOURCE="docs/planning/tasks.md"
    FALLBACK_NEXT="maintenir la prochaine action frontend executable avec preuve attendue"
    FALLBACK_ACTION="CONTINUE_FRONTEND_FROM_TASKS"
    ;;
  integrator)
    FALLBACK_SOURCE="docs/scrum/sprint-current.md"
    FALLBACK_NEXT="maintenir le plan d'integration inter-equipes et de handoff"
    FALLBACK_ACTION="CONTINUE_INTEGRATOR_FROM_SPRINT"
    ;;
  data_analyst)
    FALLBACK_SOURCE="data"
    FALLBACK_NEXT="maintenir la prochaine action data exploitable pour produit/qa"
    FALLBACK_ACTION="CONTINUE_DATA_ANALYST_FROM_DATASET"
    ;;
  infra_engineer)
    FALLBACK_SOURCE="docs/ops"
    FALLBACK_NEXT="maintenir la prochaine action infra/cicd pour accelerer la livraison"
    FALLBACK_ACTION="CONTINUE_INFRA_FROM_OPS"
    ;;
  tester)
    FALLBACK_SOURCE="copilot-app/backend/tests"
    FALLBACK_NEXT="maintenir plan de tests minimal pour prochain item READY"
    FALLBACK_ACTION="CONTINUE_TESTER_FROM_TEST_TREE"
    ;;
  qa)
    FALLBACK_SOURCE="finance-app/openclaw-gates"
    FALLBACK_NEXT="contrôler cohérence VERDICT/BLOCKER_ID au prochain tick"
    FALLBACK_ACTION="CONTINUE_QA_FROM_GATES"
    ;;
  architect)
    FALLBACK_SOURCE="docs/ops/API_ENDPOINT_BEST_PRACTICES.md"
    FALLBACK_NEXT="produire un gate architecture aligné best-practices sur le prochain scope READY"
    FALLBACK_ACTION="CONTINUE_ARCHITECT_ARCH_GUARDRAIL_REVIEW"
    ;;
  po)
    FALLBACK_SOURCE="docs/planning/mvp-plan.md"
    FALLBACK_NEXT="reconfirmer les priorités backlog orientées valeur"
    FALLBACK_ACTION="CONTINUE_PO_FROM_MVP_PLAN"
    ;;
  scrum_master)
    FALLBACK_SOURCE="docs/scrum/sprint-current.md"
    FALLBACK_NEXT="maintenir cadence et réduction des blockers/WIP"
    FALLBACK_ACTION="CONTINUE_SCRUM_MASTER_FROM_SPRINT_STATE"
    ;;
  clawsentinel)
    FALLBACK_SOURCE="docs/orchestrator-ops/agent-watchdog.md"
    FALLBACK_NEXT="vérifier dérive cron et publier action anti-drift unique"
    FALLBACK_ACTION="CONTINUE_CLAWSENTINEL_FROM_WATCHDOG"
    ;;
esac

FALLBACK_ARTIFACT_MARKER="$(required_artifact_marker_for_role "$ROLE")"
FALLBACK_ARTIFACT_VALUE="${FALLBACK_SOURCE:-unknown}"

if [[ -n "$FALLBACK_SOURCE" && -e "$FALLBACK_SOURCE" ]]; then
  FAIL_COUNT="$(( $(read_fail_count) + 1 ))"
  write_fail_count "$FAIL_COUNT"
  RECOVERY_NOTE="$(sanitize_evidence_fragment "$(recover_role_if_needed "$FAIL_COUNT")")"
  EVIDENCE_TEXT="fallback_mode=checkpoint; source_ok=${FALLBACK_SOURCE}; signal_unparseable=1; output_channel=${OUTPUT_CHANNEL_LABEL}; rc_primary=${RC_PRIMARY}; rc_retry=${RC_RETRY}; rc_codex=${RC_CODEX_FALLBACK}; retry_mode=${RETRY_MODE}; t_primary=${PROMPT_TIMEOUT_SECONDS}s; t_retry=${RETRY_PROMPT_TIMEOUT_SECONDS}s; t_codex=${CODEX_FALLBACK_TIMEOUT}s; fail_count=${FAIL_COUNT}/${RECOVERY_THRESHOLD}; raw_primary=[${PRIMARY_PREVIEW:-n/a}]; raw_retry=[${RETRY_PREVIEW:-n/a}]; raw_codex=[${CODEX_PREVIEW:-n/a}]; task_update=none_no_signal; lock_check=ok; ${FALLBACK_ARTIFACT_MARKER}${FALLBACK_ARTIFACT_VALUE}; ${STARTUP_NOTE_SAFE}; ${RECOVERY_NOTE}"
else
  FAIL_COUNT="$(( $(read_fail_count) + 1 ))"
  write_fail_count "$FAIL_COUNT"
  RECOVERY_NOTE="$(sanitize_evidence_fragment "$(recover_role_if_needed "$FAIL_COUNT")")"
  EVIDENCE_TEXT="fallback_mode=checkpoint; source_missing=${FALLBACK_SOURCE:-unknown}; signal_unparseable=1; output_channel=${OUTPUT_CHANNEL_LABEL}; rc_primary=${RC_PRIMARY}; rc_retry=${RC_RETRY}; rc_codex=${RC_CODEX_FALLBACK}; retry_mode=${RETRY_MODE}; t_primary=${PROMPT_TIMEOUT_SECONDS}s; t_retry=${RETRY_PROMPT_TIMEOUT_SECONDS}s; t_codex=${CODEX_FALLBACK_TIMEOUT}s; fail_count=${FAIL_COUNT}/${RECOVERY_THRESHOLD}; raw_primary=[${PRIMARY_PREVIEW:-n/a}]; raw_retry=[${RETRY_PREVIEW:-n/a}]; raw_codex=[${CODEX_PREVIEW:-n/a}]; task_update=none_no_signal; lock_check=ok; ${FALLBACK_ARTIFACT_MARKER}${FALLBACK_ARTIFACT_VALUE}; ${STARTUP_NOTE_SAFE}; ${RECOVERY_NOTE}"
fi
trace_event "checkpoint_fallback rc_primary=${RC_PRIMARY} rc_retry=${RC_RETRY} rc_codex=${RC_CODEX_FALLBACK} fail_count=${FAIL_COUNT}/${RECOVERY_THRESHOLD} retry_mode=${RETRY_MODE}"

FALLBACK_OUTPUT="$(cat <<EOF
STATUS: IN_PROGRESS
DELTA: NO_DELTA
EVIDENCE: ${EVIDENCE_TEXT}
RISKS: réponse tmux non exploitable sur ce tick, continuité basée checkpoint
NEXT: ${FALLBACK_NEXT:-relancer le prochain tick}
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: ${FALLBACK_ACTION:-CONTINUE_${ROLE}_FROM_CHECKPOINT}
EOF
)"

FALLBACK_OUTPUT="$(printf "%s\n" "$FALLBACK_OUTPUT" | reconcile_runtime_truth)"
FALLBACK_OUTPUT="$(apply_no_delta_gate "$FALLBACK_OUTPUT" "fallback_checkpoint")"
FALLBACK_OUTPUT="$(printf "%s\n" "$FALLBACK_OUTPUT" | enforce_role_delivery_contract "fallback_checkpoint")"
sanitize_tmux_logs
persist_last_contract "$FALLBACK_OUTPUT"
trace_event "final_output source=checkpoint"
printf "%s\n" "$FALLBACK_OUTPUT"
