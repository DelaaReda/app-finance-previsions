#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
cd "$ROOT"

API_BASE_URL="${FC_API_BASE_URL:-http://127.0.0.1:8050}"
MONITOR_BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
ARTIFACT_DIR="${FC_RUNTIME_GATE_ARTIFACT_DIR:-$ROOT/evidence/runtime-gates}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARTIFACT_FILE="${ARTIFACT_DIR}/runtime-gate-${TIMESTAMP}.json"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$ARTIFACT_DIR"

set +e
./finance-copilot.sh start
START_RC=$?
set -e

set +e
MONITOR_SUMMARY="$(bash scripts/monitor_contract_smoke.sh --base-url "$MONITOR_BASE_URL" 2>&1)"
MONITOR_RC=$?
set -e
printf '%s' "$MONITOR_SUMMARY" > "${TMP_DIR}/monitor_summary.txt"

set +e
ENDPOINT_SUMMARY="$(bash scripts/critical_endpoints_smoke.sh --base-url "$API_BASE_URL" 2>&1)"
ENDPOINT_RC=$?
set -e
printf '%s' "$ENDPOINT_SUMMARY" > "${TMP_DIR}/endpoint_summary.txt"

set +e
DOCTOR_JSON="$(bash scripts/fc_doctor.sh --json 2>&1)"
DOCTOR_RC=$?
set -e
printf '%s' "$DOCTOR_JSON" > "${TMP_DIR}/doctor_json.txt"

set +e
STATUS_JSON="$(curl -fsSL --max-time 4 "${MONITOR_BASE_URL%/}/api/status" 2>&1)"
STATUS_RC=$?
set -e
printf '%s' "$STATUS_JSON" > "${TMP_DIR}/status_json.txt"

VERDICT="OK"
if [[ "$START_RC" -ne 0 || "$MONITOR_RC" -ne 0 || "$ENDPOINT_RC" -ne 0 || "$DOCTOR_RC" -ne 0 || "$STATUS_RC" -ne 0 ]]; then
  VERDICT="DEGRADED"
fi

python3 - "$ARTIFACT_FILE" "$VERDICT" "$START_RC" "$MONITOR_RC" "$ENDPOINT_RC" "$DOCTOR_RC" "$STATUS_RC" "$API_BASE_URL" "$MONITOR_BASE_URL" "$TMP_DIR" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    artifact_file,
    verdict,
    start_rc,
    monitor_rc,
    endpoint_rc,
    doctor_rc,
    status_rc,
    api_base,
    monitor_base,
    tmp_dir,
) = sys.argv[1:]

tmp_dir_path = Path(tmp_dir)
monitor_summary = (tmp_dir_path / "monitor_summary.txt").read_text(encoding="utf-8", errors="replace")
endpoint_summary = (tmp_dir_path / "endpoint_summary.txt").read_text(encoding="utf-8", errors="replace")
doctor_json_raw = (tmp_dir_path / "doctor_json.txt").read_text(encoding="utf-8", errors="replace")
status_json_raw = (tmp_dir_path / "status_json.txt").read_text(encoding="utf-8", errors="replace")

doctor_payload = {
    "status": "error",
    "raw": doctor_json_raw,
}
try:
    parsed = json.loads(doctor_json_raw)
    if isinstance(parsed, dict):
        doctor_payload = parsed
except Exception:
    pass

status_payload = {
    "status": "error",
    "raw": status_json_raw,
    "po_scrum_master": {},
}
try:
    parsed = json.loads(status_json_raw)
    if isinstance(parsed, dict):
        status_payload = {
            "status": str(parsed.get("health", "unknown")).lower(),
            "po_scrum_master": parsed.get("po_scrum_master", {}) if isinstance(parsed.get("po_scrum_master"), dict) else {},
        }
except Exception:
    pass

payload = {
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "verdict": verdict,
    "services": {
        "launcher_start_rc": int(start_rc),
        "api_base_url": api_base,
        "monitor_base_url": monitor_base,
    },
    "checks": {
        "monitor_contract": {
            "rc": int(monitor_rc),
            "summary": monitor_summary,
        },
        "critical_endpoints": {
            "rc": int(endpoint_rc),
            "summary": endpoint_summary,
        },
        "doctor": {
            "rc": int(doctor_rc),
            "summary": doctor_payload,
        },
        "status_api": {
            "rc": int(status_rc),
            "summary": status_payload,
        },
    },
}

Path(artifact_file).write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=True))
PY

echo "runtime_gate verdict=${VERDICT} artifact=${ARTIFACT_FILE}"
echo "monitor: ${MONITOR_SUMMARY}"
echo "endpoints: ${ENDPOINT_SUMMARY}"
echo "doctor: ${DOCTOR_JSON}"
echo "status: ${STATUS_JSON}"

if [[ "$VERDICT" != "OK" ]]; then
  exit 1
fi
