#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
cd "$ROOT"

BASE_URL="${FC_API_BASE_URL:-http://127.0.0.1:8050}"
TIMEOUT_SECONDS="${FC_ENDPOINT_SMOKE_TIMEOUT_SECONDS:-12}"
STOCKS_TIMEOUT_SECONDS="${FC_ENDPOINT_STOCKS_TIMEOUT_SECONDS:-30}"
QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-$BASE_URL}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-$TIMEOUT_SECONDS}"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: bash scripts/critical_endpoints_smoke.sh [--base-url URL] [--timeout SEC] [--quiet]" >&2
      exit 2
      ;;
  esac
done

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "Invalid timeout: $TIMEOUT_SECONDS" >&2
  exit 2
fi
if ! [[ "$STOCKS_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "Invalid stocks timeout: $STOCKS_TIMEOUT_SECONDS" >&2
  exit 2
fi

ENDPOINTS=(
  "/api/status"
  "/api/forecasts?horizon=short&limit=24"
  "/api/recommendations/daily?limit=3"
  "/api/portfolios"
  "/api/ingestion/health"
)

declare -a RESULTS=()
FAILURES=0
DEGRADED_COUNT=0

for endpoint in "${ENDPOINTS[@]}"; do
  url="${BASE_URL%/}${endpoint}"
  response_file="$(mktemp)"
  status_code="$(curl -sS --max-time "$TIMEOUT_SECONDS" -o "$response_file" -w "%{http_code}" "$url" || true)"
  body="$(cat "$response_file" 2>/dev/null || true)"
  rm -f "$response_file"

  if [[ "$status_code" != "200" ]]; then
    RESULTS+=("FAIL ${endpoint} http=${status_code}")
    FAILURES=$((FAILURES + 1))
    continue
  fi

  check="$(
python3 - "$endpoint" "$body" <<'PY'
import json
import sys

endpoint = sys.argv[1]
raw = sys.argv[2]
try:
    payload = json.loads(raw)
except Exception as exc:
    print(f"FAIL {endpoint} invalid_json:{exc}")
    raise SystemExit(1)

if not isinstance(payload, dict):
    print(f"FAIL {endpoint} payload_not_object")
    raise SystemExit(1)

if "ok" not in payload:
    print(f"FAIL {endpoint} missing_ok")
    raise SystemExit(1)
if "data" not in payload:
    print(f"FAIL {endpoint} missing_data")
    raise SystemExit(1)

strict_endpoints = {
    "/api/forecasts?horizon=short&limit=24",
    "/api/recommendations/daily?limit=3",
}

status = payload.get("status")
error_obj = payload.get("error")
strict = endpoint in strict_endpoints

if strict:
    if "status" not in payload:
        print(f"FAIL {endpoint} missing_status")
        raise SystemExit(1)
    if status not in {"ok", "degraded", "error"}:
        print(f"FAIL {endpoint} invalid_status:{status}")
        raise SystemExit(1)
    if "meta" not in payload or not isinstance(payload.get("meta"), dict):
        print(f"FAIL {endpoint} missing_meta")
        raise SystemExit(1)
    meta = payload.get("meta") or {}
    for key in ("source", "request_id", "schema_version", "fallback"):
        if key not in meta:
            print(f"FAIL {endpoint} meta_missing_{key}")
            raise SystemExit(1)
    if status in {"degraded", "error"}:
        if not isinstance(error_obj, dict):
            print(f"FAIL {endpoint} degraded_without_error_object")
            raise SystemExit(1)
        if "code" not in error_obj or "message" not in error_obj:
            print(f"FAIL {endpoint} degraded_error_shape_invalid")
            raise SystemExit(1)
        print(f"DEGRADED {endpoint} code={error_obj.get('code')}")
    else:
        print(f"PASS_STRICT {endpoint}")
    raise SystemExit(0)

if status in {"degraded", "error"}:
    if isinstance(error_obj, dict) and "code" in error_obj and "message" in error_obj:
        print(f"DEGRADED {endpoint} code={error_obj.get('code')}")
    else:
        print(f"DEGRADED {endpoint} code=compat_endpoint")
else:
    print(f"PASS_COMPAT {endpoint}")
PY
)"
  rc=$?
  if [[ $rc -ne 0 ]]; then
    RESULTS+=("$check")
    FAILURES=$((FAILURES + 1))
  else
    RESULTS+=("$check")
    if [[ "$check" == DEGRADED* ]]; then
      DEGRADED_COUNT=$((DEGRADED_COUNT + 1))
    fi
  fi
done

SUMMARY="PASS base=${BASE_URL} endpoints=${#ENDPOINTS[@]} degraded=${DEGRADED_COUNT}"
if [[ "$FAILURES" -gt 0 ]]; then
  SUMMARY="FAIL base=${BASE_URL} failures=${FAILURES} degraded=${DEGRADED_COUNT}"
fi

if [[ "$QUIET" -eq 0 ]]; then
  echo "$SUMMARY"
  printf '%s\n' "${RESULTS[@]}"
fi

if [[ "$FAILURES" -gt 0 ]]; then
  exit 1
fi
