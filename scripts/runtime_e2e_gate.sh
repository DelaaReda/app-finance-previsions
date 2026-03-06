#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
cd "$ROOT"

MONITOR_BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
API_BASE_URL="${FC_GATE_API_BASE_URL:-http://127.0.0.1:8050}"
PROOF_ROOT="${FC_GATE_PROOF_ROOT:-$ROOT/docs/operations/orchestrator/proofs/runtime-gate}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
PROOF_FILE="$PROOF_ROOT/runtime-e2e-$TS_UTC.log"
SUMMARY_JSON="$PROOF_ROOT/runtime-e2e-$TS_UTC.json"

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
record_cmd "launcher_start ./finance-copilot.sh start" ./finance-copilot.sh start
record_cmd "launcher_status ./finance-copilot.sh status" ./finance-copilot.sh status
record_cmd "monitor_smoke scripts/monitor_contract_smoke.sh" bash scripts/monitor_contract_smoke.sh --base-url "$MONITOR_BASE_URL"
doctor_json_file="$tmp_dir/doctor.json"
log "doctor scripts/fc_doctor.sh --json"
if ! bash scripts/fc_doctor.sh --json >"$doctor_json_file" 2>>"$PROOF_FILE"; then
  log "doctor_command_exit_nonzero tolerated_for_gate"
fi
if [[ -s "$doctor_json_file" ]]; then
  cat "$doctor_json_file" | tee -a "$PROOF_FILE" >/dev/null
fi

failures=0
check_endpoint "forecasts" "$API_BASE_URL/api/forecasts?horizon=short&limit=24" || failures=$((failures+1))
check_endpoint "recommendations_daily" "$API_BASE_URL/api/recommendations/daily?limit=3" || failures=$((failures+1))
check_endpoint "stocks_sheet" "$API_BASE_URL/api/stocks/SPY/sheet" || failures=$((failures+1))

log "fetch_status_snapshot $MONITOR_BASE_URL/api/status"
curl -sS --max-time 20 "$MONITOR_BASE_URL/api/status" | tee -a "$PROOF_FILE" >/dev/null
log "fetch_runtime_diagnostics $MONITOR_BASE_URL/api/runtime-diagnostics"
curl -sS --max-time 20 "$MONITOR_BASE_URL/api/runtime-diagnostics" | tee -a "$PROOF_FILE" >/dev/null

doctor_status="$(python3 - "$doctor_json_file" <<'PY'
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
print(str(payload.get("status","unknown")).lower())
PY
)"
[[ -n "$doctor_status" ]] || doctor_status="unknown"

global_result="OK"
if [[ "$doctor_status" == "failed" || "$doctor_status" == "error" ]]; then
  global_result="FAILED"
elif [[ "$doctor_status" != "ok" ]]; then
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
  "endpoint_failures": $failures,
  "doctor_status": "$doctor_status",
  "proof_log": "$PROOF_FILE"
}
print(json.dumps(payload, ensure_ascii=True, indent=2))
PY

if [[ "$global_result" == "FAILED" ]]; then
  log "runtime_e2e_gate result=FAILED endpoint_failures=$failures doctor_status=$doctor_status proof=$PROOF_FILE summary=$SUMMARY_JSON"
  exit 2
fi

if [[ "$global_result" == "DEGRADED" ]]; then
  log "runtime_e2e_gate result=DEGRADED endpoint_failures=$failures doctor_status=$doctor_status proof=$PROOF_FILE summary=$SUMMARY_JSON"
  exit 1
fi

log "runtime_e2e_gate result=OK endpoint_failures=0 doctor_status=$doctor_status proof=$PROOF_FILE summary=$SUMMARY_JSON"
