#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
cd "$ROOT"

BASE_URL="${FC_API_BASE_URL:-http://127.0.0.1:8050}"
TIMEOUT_SECONDS="${FC_DELIVERY_VALUE_TIMEOUT_SECONDS:-12}"
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
      echo "Usage: bash scripts/delivery_value_smoke.sh [--base-url URL] [--timeout SEC] [--quiet]" >&2
      exit 2
      ;;
  esac
done

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "Invalid timeout: $TIMEOUT_SECONDS" >&2
  exit 2
fi

declare -a RESULTS=()
FAILURES=0
PORTFOLIO_ID=""

fetch_json() {
  local endpoint="$1"
  local response_file
  response_file="$(mktemp)"
  local status_code
  status_code="$(curl -sS --max-time "$TIMEOUT_SECONDS" -o "$response_file" -w "%{http_code}" "${BASE_URL%/}${endpoint}" || true)"
  local body
  body="$(cat "$response_file" 2>/dev/null || true)"
  rm -f "$response_file"
  printf '%s\n%s' "$status_code" "$body"
}

copilot_raw="$(fetch_json '/api/copilot/start')"
copilot_status="${copilot_raw%%$'\n'*}"
copilot_body="${copilot_raw#*$'\n'}"
if [[ "$copilot_status" != "200" ]]; then
  RESULTS+=("FAIL /api/copilot/start http=${copilot_status}")
  FAILURES=$((FAILURES + 1))
else
  copilot_check="$(
python3 - "$copilot_body" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if not isinstance(payload, dict):
    print("FAIL /api/copilot/start payload_not_object")
    raise SystemExit(1)
if payload.get("ok") is not True:
    print("FAIL /api/copilot/start missing_ok_true")
    raise SystemExit(1)
data = payload.get("data")
if not isinstance(data, dict):
    print("FAIL /api/copilot/start missing_data_object")
    raise SystemExit(1)
brief = data.get("brief_of_day")
ask = data.get("ask")
open_actions = data.get("open")
if not isinstance(brief, dict):
    print("FAIL /api/copilot/start missing_brief_of_day")
    raise SystemExit(1)
if not isinstance(ask, list):
    print("FAIL /api/copilot/start missing_ask_list")
    raise SystemExit(1)
if not isinstance(open_actions, list):
    print("FAIL /api/copilot/start missing_open_list")
    raise SystemExit(1)
summary = str(brief.get("summary", "") or "").strip()
if not summary:
    print("FAIL /api/copilot/start empty_brief_summary")
    raise SystemExit(1)
print(f"PASS /api/copilot/start ask={len(ask)} open={len(open_actions)}")
PY
)"
  rc=$?
  RESULTS+=("$copilot_check")
  if [[ $rc -ne 0 ]]; then
    FAILURES=$((FAILURES + 1))
  fi
fi

recommendations_raw="$(fetch_json '/api/recommendations/daily?limit=3')"
recommendations_status="${recommendations_raw%%$'\n'*}"
recommendations_body="${recommendations_raw#*$'\n'}"
if [[ "$recommendations_status" != "200" ]]; then
  RESULTS+=("FAIL /api/recommendations/daily?limit=3 http=${recommendations_status}")
  FAILURES=$((FAILURES + 1))
else
  recommendations_check="$(
python3 - "$recommendations_body" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if not isinstance(payload, dict):
    print("FAIL /api/recommendations/daily?limit=3 payload_not_object")
    raise SystemExit(1)
if payload.get("ok") is not True:
    print("FAIL /api/recommendations/daily?limit=3 missing_ok_true")
    raise SystemExit(1)
if payload.get("status") not in {"ok", "degraded", "error"}:
    print(f"FAIL /api/recommendations/daily?limit=3 invalid_status:{payload.get('status')}")
    raise SystemExit(1)
meta = payload.get("meta")
if not isinstance(meta, dict):
    print("FAIL /api/recommendations/daily?limit=3 missing_meta")
    raise SystemExit(1)
data = payload.get("data")
if data is None:
    print("FAIL /api/recommendations/daily?limit=3 missing_data")
    raise SystemExit(1)
count = len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else 0
print(f"PASS /api/recommendations/daily?limit=3 status={payload.get('status')} items={count}")
PY
)"
  rc=$?
  RESULTS+=("$recommendations_check")
  if [[ $rc -ne 0 ]]; then
    FAILURES=$((FAILURES + 1))
  fi
fi

portfolios_raw="$(fetch_json '/api/portfolios')"
portfolios_status="${portfolios_raw%%$'\n'*}"
portfolios_body="${portfolios_raw#*$'\n'}"
if [[ "$portfolios_status" != "200" ]]; then
  RESULTS+=("FAIL /api/portfolios http=${portfolios_status}")
  FAILURES=$((FAILURES + 1))
else
  portfolios_check="$(
python3 - "$portfolios_body" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if not isinstance(payload, dict):
    print("FAIL /api/portfolios payload_not_object")
    raise SystemExit(1)
if payload.get("ok") is not True:
    print("FAIL /api/portfolios missing_ok_true")
    raise SystemExit(1)
data = payload.get("data")
if not isinstance(data, dict):
    print("FAIL /api/portfolios missing_data_object")
    raise SystemExit(1)
portfolios = data.get("portfolios")
if not isinstance(portfolios, list):
    print("FAIL /api/portfolios missing_portfolios_list")
    raise SystemExit(1)
if not portfolios:
    print("FAIL /api/portfolios no_portfolios_seeded")
    raise SystemExit(1)
first = portfolios[0] if isinstance(portfolios[0], dict) else {}
portfolio_id = str(first.get("id", "") or "").strip()
if not portfolio_id:
    print("FAIL /api/portfolios missing_first_portfolio_id")
    raise SystemExit(1)
print(f"PASS /api/portfolios count={len(portfolios)} id={portfolio_id}")
PY
)"
  rc=$?
  RESULTS+=("$portfolios_check")
  if [[ $rc -ne 0 ]]; then
    FAILURES=$((FAILURES + 1))
  else
    PORTFOLIO_ID="${portfolios_check##* id=}"
  fi
fi

if [[ -n "$PORTFOLIO_ID" ]]; then
  risk_raw="$(fetch_json "/api/portfolios/${PORTFOLIO_ID}/risk-profile?benchmark=SPY")"
  risk_status="${risk_raw%%$'\n'*}"
  risk_body="${risk_raw#*$'\n'}"
  if [[ "$risk_status" != "200" ]]; then
    RESULTS+=("FAIL /api/portfolios/${PORTFOLIO_ID}/risk-profile?benchmark=SPY http=${risk_status}")
    FAILURES=$((FAILURES + 1))
  else
    risk_check="$(
python3 - "$PORTFOLIO_ID" "$risk_body" <<'PY'
import json
import sys

portfolio_id = sys.argv[1]
payload = json.loads(sys.argv[2])
endpoint = f"/api/portfolios/{portfolio_id}/risk-profile?benchmark=SPY"
if not isinstance(payload, dict):
    print(f"FAIL {endpoint} payload_not_object")
    raise SystemExit(1)
if payload.get("ok") is not True:
    print(f"FAIL {endpoint} missing_ok_true")
    raise SystemExit(1)
data = payload.get("data")
if not isinstance(data, dict):
    print(f"FAIL {endpoint} missing_data_object")
    raise SystemExit(1)
for key in ("risk_profile", "risk_level", "why"):
    if key not in data:
        print(f"FAIL {endpoint} missing_{key}")
        raise SystemExit(1)
why = data.get("why")
if not isinstance(why, list) or not why:
    print(f"FAIL {endpoint} empty_why")
    raise SystemExit(1)
print(
    f"PASS {endpoint} profile={data.get('risk_profile')} "
    f"level={data.get('risk_level')}"
)
PY
)"
    rc=$?
    RESULTS+=("$risk_check")
    if [[ $rc -ne 0 ]]; then
      FAILURES=$((FAILURES + 1))
    fi
  fi
fi

SUMMARY="PASS base=${BASE_URL} checks=${#RESULTS[@]}"
if [[ "$FAILURES" -gt 0 ]]; then
  SUMMARY="FAIL base=${BASE_URL} failures=${FAILURES}"
fi

if [[ "$QUIET" -eq 0 ]]; then
  echo "$SUMMARY"
  printf '%s\n' "${RESULTS[@]}"
fi

if [[ "$FAILURES" -gt 0 ]]; then
  exit 1
fi
