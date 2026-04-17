#!/usr/bin/env bash
# MODE: PUBLIC_VALIDATION
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-${FC_API_BASE_URL:-${FC_PUBLIC_APP_BASE_URL:-http://3.98.20.77}}}}"
QUESTION="${QUESTION:-Donne une recommandation courte sur NVDA avec risques principaux.}"
TICKERS_JSON='["NVDA"]'

if [[ "${FC_ALLOW_LOCAL_URLS:-0}" != "1" && "$BASE_URL" =~ ^https?://(127\.0\.0\.1|localhost)(:|/|$) ]]; then
  echo "Refusing local validation URL: $BASE_URL (set FC_ALLOW_LOCAL_URLS=1 to override)" >&2
  exit 2
fi

payload=$(cat <<JSON
{"question":"${QUESTION}","tickers":${TICKERS_JSON},"max_sources":5}
JSON
)

resp="$(curl -sS -X POST "${BASE_URL}/api/copilot/ask" -H 'Content-Type: application/json' -d "$payload")"

python3 - <<'PY' "$resp" "$BASE_URL"
import json
import sys

raw = json.loads(sys.argv[1])
base_url = sys.argv[2]
data = raw.get("data") if isinstance(raw, dict) and isinstance(raw.get("data"), dict) else raw
if not isinstance(data, dict):
    raise SystemExit("CONTRACT_FAIL payload data is not an object")

required = ["verdict", "confidence", "why", "risk"]
missing = [k for k in required if k not in data]
if missing:
    raise SystemExit(f"CONTRACT_FAIL missing keys: {','.join(missing)}")

why = data.get("why")
if not isinstance(why, list) or not why:
    raise SystemExit("CONTRACT_FAIL key 'why' must be a non-empty list")

risk = data.get("risk")
if not isinstance(risk, dict):
    raise SystemExit("CONTRACT_FAIL key 'risk' must be an object")
if "level" not in risk or "caveat" not in risk:
    raise SystemExit("CONTRACT_FAIL risk object must contain level and caveat")

confidence = data.get("confidence")
try:
    float(confidence)
except Exception:
    raise SystemExit("CONTRACT_FAIL confidence must be numeric")

verdict = str(data.get("verdict") or "").strip().lower()
if verdict not in {"buy", "sell", "hold"}:
    raise SystemExit(f"CONTRACT_FAIL verdict unexpected: {verdict}")

print(f"CONTRACT_PASS base_url={base_url} verdict={verdict} confidence={confidence} why_items={len(why)} risk_level={risk.get('level')}")
PY
