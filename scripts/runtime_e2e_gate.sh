#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
cd "$ROOT"

MONITOR_BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
API_BASE_URL="${FC_GATE_API_BASE_URL:-http://127.0.0.1:8050}"
FRONTEND_BASE_URL="${FC_GATE_FRONTEND_BASE_URL:-http://127.0.0.1:5173}"
BACKEND_HEALTH_URL="${FC_GATE_BACKEND_HEALTH_URL:-$API_BASE_URL/api/health}"
QUIET_PERIOD_SECONDS="${FC_GATE_QUIET_PERIOD_SECONDS:-30}"
FRONTEND_LOG="${FC_GATE_FRONTEND_LOG:-/tmp/frontend.log}"
PROOF_ROOT="${FC_GATE_PROOF_ROOT:-$ROOT/docs/operations/orchestrator/proofs/runtime-gate}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
PROOF_FILE="$PROOF_ROOT/runtime-e2e-$TS_UTC.log"
SUMMARY_JSON="$PROOF_ROOT/runtime-e2e-$TS_UTC.json"

if ! [[ "$QUIET_PERIOD_SECONDS" =~ ^[0-9]+$ ]]; then
  QUIET_PERIOD_SECONDS=30
fi

mkdir -p "$PROOF_ROOT"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

log() {
  echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$PROOF_FILE"
}

record_cmd() {
  local label="$1"
  shift
  log "$label"
  "$@" 2>&1 | tee -a "$PROOF_FILE"
}

probe_http_code() {
  local url="$1"
  curl -sS --max-time 10 -o /dev/null -w "%{http_code}" "$url" || true
}

listener_up() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :$port )" 2>/dev/null | awk 'NR>1 {found=1} END {exit(found ? 0 : 1)}'
    return $?
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

runtime_stack_probe() {
  local frontend_code backend_code monitor_code
  local listener_frontend="down"
  local listener_backend="down"
  local listener_monitor="down"

  frontend_code="$(probe_http_code "$FRONTEND_BASE_URL/")"
  backend_code="$(probe_http_code "$BACKEND_HEALTH_URL")"
  monitor_code="$(probe_http_code "$MONITOR_BASE_URL/api/status")"

  listener_up 5173 && listener_frontend="up"
  listener_up 8050 && listener_backend="up"
  listener_up 7779 && listener_monitor="up"

  printf '%s|%s|%s|%s|%s|%s\n' \
    "$frontend_code" \
    "$backend_code" \
    "$monitor_code" \
    "$listener_frontend" \
    "$listener_backend" \
    "$listener_monitor"
}

check_endpoint() {
  local name="$1"
  local url="$2"
  local body_file="$tmp_dir/${name}.json"
  local status_file="$tmp_dir/${name}.status"
  local code="000"
  code="$(curl -sS --max-time 20 -o "$body_file" -w "%{http_code}" "$url" || true)"
  printf "%s" "$code" > "$status_file"

  local verdict="PASS"
  local reason="ok"

  if [[ "$code" != "200" ]]; then
    verdict="DEGRADED"
    reason="http_${code}"
  else
    if ! python3 - "$body_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="ignore").strip()
if not raw:
    print("empty_body")
    raise SystemExit(1)
try:
    payload = json.loads(raw)
except Exception:
    print("invalid_json")
    raise SystemExit(1)
if not isinstance(payload, dict):
    print("payload_not_object")
    raise SystemExit(1)

has_envelope = isinstance(payload.get("ok"), bool) and "data" in payload
has_degraded_contract = all(k in payload for k in ("status", "data", "error", "meta"))
has_raw_not_found = payload.get("detail") == "Not Found" or "HTTP 404 Not Found" in raw

if has_raw_not_found:
    print("raw_not_found_contract")
    raise SystemExit(1)
if has_envelope or has_degraded_contract:
    print("contract_ok")
    raise SystemExit(0)

print("contract_unexpected_shape")
raise SystemExit(1)
PY
    then
      verdict="DEGRADED"
      reason="contract_invalid"
    fi
  fi

  log "endpoint[$name] verdict=$verdict reason=$reason url=$url"
  if [[ -s "$body_file" ]]; then
    log "endpoint[$name] sample=$(head -c 220 "$body_file" | tr '\n' ' ')"
  fi

  if [[ "$verdict" != "PASS" ]]; then
    return 1
  fi
  return 0
}

log "runtime_e2e_gate started ts_utc=$TS_UTC"
launcher_action="skipped"
preflight_probe="$(runtime_stack_probe)"
IFS='|' read -r preflight_frontend_code preflight_backend_code preflight_monitor_code preflight_listener_5173 preflight_listener_8050 preflight_listener_7779 <<< "$preflight_probe"
log "preflight_stack frontend=${preflight_frontend_code} backend=${preflight_backend_code} monitor=${preflight_monitor_code} listeners=5173:${preflight_listener_5173},8050:${preflight_listener_8050},7779:${preflight_listener_7779}"
if [[ "$preflight_frontend_code" == "200" && "$preflight_backend_code" == "200" && "$preflight_monitor_code" == "200" && "$preflight_listener_5173" == "up" && "$preflight_listener_8050" == "up" && "$preflight_listener_7779" == "up" ]]; then
  log "launcher_skip reason=stack_already_healthy"
else
  launcher_action="started"
  record_cmd "launcher_start ./finance-copilot.sh start" ./finance-copilot.sh start
fi
record_cmd "launcher_status ./finance-copilot.sh status" ./finance-copilot.sh status
record_cmd "monitor_smoke scripts/monitor_contract_smoke.sh" bash scripts/monitor_contract_smoke.sh --base-url "$MONITOR_BASE_URL"
doctor_json_file="$tmp_dir/doctor.json"
doctor_eval_file="$tmp_dir/doctor_eval.json"
log "doctor scripts/fc_doctor.sh --json"
if ! bash scripts/fc_doctor.sh --json >"$doctor_json_file" 2>>"$PROOF_FILE"; then
  log "doctor_command_exit_nonzero tolerated_for_gate"
fi
if [[ -s "$doctor_json_file" ]]; then
  cat "$doctor_json_file" | tee -a "$PROOF_FILE" >/dev/null
fi
python3 - "$doctor_json_file" <<'PY' > "$doctor_eval_file"
import json
import sys
from pathlib import Path

runtime_scope = {
    "workspace_root",
    "runtime_state",
    "scheduler_authority",
    "sessions",
    "locks",
    "queue_workboard",
    "providers",
    "product_value",
}

path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="ignore").strip() if path.exists() else ""
payload = {}
if raw:
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {}

overall = str(payload.get("status", "unknown")).lower() if isinstance(payload, dict) else "unknown"
checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
if not isinstance(checks, dict):
    checks = {}

def normalize_status(value: str) -> str:
    token = str(value or "").strip().lower()
    if token in {"ok", "pass", "healthy"}:
        return "ok"
    if token in {"failed", "error"}:
        return "failed"
    if token:
        return "degraded"
    return "unknown"

runtime_status = "ok"
runtime_degraded_checks = []
non_runtime_degraded_checks = []

for name, detail in checks.items():
    status = normalize_status(detail.get("status") if isinstance(detail, dict) else detail)
    if name in runtime_scope:
        if status == "failed":
            runtime_status = "failed"
        elif status != "ok" and runtime_status != "failed":
            runtime_status = "degraded"
            runtime_degraded_checks.append(name)
    elif status != "ok":
        non_runtime_degraded_checks.append(name)

if overall == "failed":
    runtime_status = "failed"
elif overall == "unknown" and runtime_status == "ok":
    runtime_status = "unknown"

print(
    json.dumps(
        {
            "doctor_status": overall or "unknown",
            "doctor_runtime_status": runtime_status,
            "doctor_runtime_degraded_checks": runtime_degraded_checks,
            "doctor_non_runtime_degraded_checks": non_runtime_degraded_checks,
        },
        ensure_ascii=True,
    )
)
PY

failures=0
quiet_period_result="SKIP"
quiet_period_reason="disabled"
quiet_frontend_code=""
quiet_monitor_code=""
quiet_backend_code=""
listener_5173="unknown"
listener_7779="unknown"
listener_8050="unknown"
check_endpoint "forecasts" "$API_BASE_URL/api/forecasts?horizon=short&limit=24" || failures=$((failures+1))
check_endpoint "recommendations_daily" "$API_BASE_URL/api/recommendations/daily?limit=3" || failures=$((failures+1))
check_endpoint "stocks_sheet" "$API_BASE_URL/api/stocks/SPY/sheet" || failures=$((failures+1))

log "fetch_status_snapshot $MONITOR_BASE_URL/api/status"
curl -sS --max-time 20 "$MONITOR_BASE_URL/api/status" | tee -a "$PROOF_FILE" >/dev/null
log "fetch_runtime_diagnostics $MONITOR_BASE_URL/api/runtime-diagnostics"
curl -sS --max-time 20 "$MONITOR_BASE_URL/api/runtime-diagnostics" | tee -a "$PROOF_FILE" >/dev/null

if [[ "$QUIET_PERIOD_SECONDS" =~ ^[0-9]+$ ]] && [[ "$QUIET_PERIOD_SECONDS" -gt 0 ]]; then
  quiet_period_result="PASS"
  quiet_period_reason="ok"
  log "quiet_period sleep=${QUIET_PERIOD_SECONDS}s"
  sleep "$QUIET_PERIOD_SECONDS"

  quiet_frontend_code="$(probe_http_code "$FRONTEND_BASE_URL/")"
  quiet_monitor_code="$(probe_http_code "$MONITOR_BASE_URL/api/status")"
  quiet_backend_code="$(probe_http_code "$BACKEND_HEALTH_URL")"

  listener_5173="down"
  listener_7779="down"
  listener_8050="down"
  listener_up 5173 && listener_5173="up"
  listener_up 7779 && listener_7779="up"
  listener_up 8050 && listener_8050="up"

  if [[ "$quiet_frontend_code" != "200" ]]; then
    quiet_period_result="DEGRADED"
    quiet_period_reason="frontend_http_${quiet_frontend_code}"
  elif [[ "$quiet_monitor_code" != "200" ]]; then
    quiet_period_result="DEGRADED"
    quiet_period_reason="monitor_http_${quiet_monitor_code}"
  elif [[ "$quiet_backend_code" != "200" ]]; then
    quiet_period_result="DEGRADED"
    quiet_period_reason="backend_http_${quiet_backend_code}"
  elif [[ "$listener_5173" != "up" || "$listener_7779" != "up" || "$listener_8050" != "up" ]]; then
    quiet_period_result="DEGRADED"
    quiet_period_reason="listener_missing"
  fi

  log "quiet_period result=${quiet_period_result} reason=${quiet_period_reason} frontend=${quiet_frontend_code} monitor=${quiet_monitor_code} backend=${quiet_backend_code} listeners=5173:${listener_5173},7779:${listener_7779},8050:${listener_8050}"
  if [[ -f "$FRONTEND_LOG" ]]; then
    log "frontend_log_tail begin path=$FRONTEND_LOG"
    while IFS= read -r line; do
      log "frontend_log $line"
    done < <(tail -n 20 "$FRONTEND_LOG")
    log "frontend_log_tail end"
  fi

  if [[ "$quiet_period_result" != "PASS" ]]; then
    failures=$((failures + 1))
  fi
fi

doctor_status="$(python3 - "$doctor_eval_file" <<'PY'
import json,sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="ignore").strip() if path.exists() else ""
if not raw:
    print("unknown")
    raise SystemExit(0)
try:
    payload=json.loads(raw)
except Exception:
    print("unknown")
    raise SystemExit(0)
print(str(payload.get("doctor_status","unknown")).lower())
PY
)"
[[ -n "$doctor_status" ]] || doctor_status="unknown"
doctor_runtime_status="$(python3 - "$doctor_eval_file" <<'PY'
import json,sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="ignore").strip() if path.exists() else ""
if not raw:
    print("unknown")
    raise SystemExit(0)
try:
    payload=json.loads(raw)
except Exception:
    print("unknown")
    raise SystemExit(0)
print(str(payload.get("doctor_runtime_status","unknown")).lower())
PY
)"
[[ -n "$doctor_runtime_status" ]] || doctor_runtime_status="unknown"
doctor_non_runtime_degraded_checks="$(python3 - "$doctor_eval_file" <<'PY'
import json,sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="ignore").strip() if path.exists() else ""
if not raw:
    print("")
    raise SystemExit(0)
try:
    payload=json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)
items = payload.get("doctor_non_runtime_degraded_checks", [])
if not isinstance(items, list):
    items = []
print(",".join(str(item).strip() for item in items if str(item).strip()))
PY
)"
doctor_non_runtime_degraded_checks_json="$(python3 - "$doctor_eval_file" <<'PY'
import json,sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="ignore").strip() if path.exists() else ""
items = []
if raw:
    try:
        payload=json.loads(raw)
        items = payload.get("doctor_non_runtime_degraded_checks", [])
        if not isinstance(items, list):
            items = []
    except Exception:
        items = []
print(json.dumps([str(item) for item in items], ensure_ascii=True))
PY
)"
[[ -n "$doctor_non_runtime_degraded_checks_json" ]] || doctor_non_runtime_degraded_checks_json="[]"
log "doctor_scope overall=${doctor_status} runtime=${doctor_runtime_status} non_runtime_checks=${doctor_non_runtime_degraded_checks:-none}"

global_result="OK"
if [[ "$doctor_runtime_status" == "failed" || "$doctor_runtime_status" == "error" ]]; then
  global_result="FAILED"
elif [[ "$doctor_runtime_status" != "ok" ]]; then
  global_result="DEGRADED"
fi
if [[ "$failures" -gt 0 && "$global_result" != "FAILED" ]]; then
  global_result="DEGRADED"
fi

python3 - <<PY > "$SUMMARY_JSON"
import json
payload = {
  "ts_utc": "$TS_UTC",
  "result": "$global_result",
  "launcher_action": "$launcher_action",
  "endpoint_failures": $failures,
  "doctor_status": "$doctor_status",
  "doctor_runtime_status": "$doctor_runtime_status",
  "doctor_non_runtime_degraded_checks": $doctor_non_runtime_degraded_checks_json,
  "proof_log": "$PROOF_FILE",
  "preflight": {
    "frontend_status": "$preflight_frontend_code",
    "backend_status": "$preflight_backend_code",
    "monitor_status": "$preflight_monitor_code",
    "listeners": {
      "5173": "$preflight_listener_5173",
      "8050": "$preflight_listener_8050",
      "7779": "$preflight_listener_7779"
    }
  },
  "quiet_period": {
    "seconds": $QUIET_PERIOD_SECONDS,
    "result": "$quiet_period_result",
    "reason": "$quiet_period_reason",
    "frontend_status": "$quiet_frontend_code",
    "monitor_status": "$quiet_monitor_code",
    "backend_status": "$quiet_backend_code",
    "listeners": {
      "5173": "$listener_5173",
      "7779": "$listener_7779",
      "8050": "$listener_8050"
    }
  }
}
print(json.dumps(payload, ensure_ascii=True, indent=2))
PY

if [[ "$global_result" == "FAILED" ]]; then
  log "runtime_e2e_gate result=FAILED endpoint_failures=$failures doctor_status=$doctor_status doctor_runtime_status=$doctor_runtime_status proof=$PROOF_FILE summary=$SUMMARY_JSON"
  exit 2
fi

if [[ "$global_result" == "DEGRADED" ]]; then
  log "runtime_e2e_gate result=DEGRADED endpoint_failures=$failures doctor_status=$doctor_status doctor_runtime_status=$doctor_runtime_status proof=$PROOF_FILE summary=$SUMMARY_JSON"
  exit 1
fi

log "runtime_e2e_gate result=OK endpoint_failures=0 doctor_status=$doctor_status doctor_runtime_status=$doctor_runtime_status proof=$PROOF_FILE summary=$SUMMARY_JSON"
