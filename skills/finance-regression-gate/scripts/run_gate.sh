#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="http://127.0.0.1:8050"
FRONTEND_URL="http://127.0.0.1:5173"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-url) BACKEND_URL="$2"; shift 2 ;;
    --frontend-url) FRONTEND_URL="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
OUT_DIR="$WORKDIR/finance-app/openclaw-gates"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_JSON="$OUT_DIR/gate-$STAMP.json"

check() {
  local name="$1"
  local url="$2"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY_RUN"
    return 0
  fi
  local code
  code="$(curl -sS -m 8 -o /tmp/gate_body.txt -w "%{http_code}" "$url" 2>/dev/null || true)"
  if [[ ! "$code" =~ ^[0-9]{3}$ ]]; then
    code="000"
  fi
  echo "$code"
}

HEALTH_CODE="$(check health "$BACKEND_URL/api/health")"
PRICES_CODE="$(check prices "$BACKEND_URL/api/stocks/prices?ticker=AAPL")"
NEWS_CODE="$(check news "$BACKEND_URL/api/news/feed")"
FORECASTS_CODE="$(check forecasts "$BACKEND_URL/api/forecasts")"
JUDGE_CODE="$(check judge "$BACKEND_URL/api/judge/quality?horizon_days=5&min_samples=20")"
FRONT_CODE="$(check frontend "$FRONTEND_URL/")"

STATUS="PASS"
for code in "$HEALTH_CODE" "$PRICES_CODE" "$NEWS_CODE" "$FORECASTS_CODE" "$JUDGE_CODE" "$FRONT_CODE"; do
  if [[ "$code" != "200" && "$code" != "DRY_RUN" ]]; then
    STATUS="FAIL"
    break
  fi
done

python3 - <<PY
import json
from pathlib import Path
out = {
  "timestamp": "${STAMP}",
  "status": "${STATUS}",
  "backend_url": "${BACKEND_URL}",
  "frontend_url": "${FRONTEND_URL}",
  "checks": {
    "health": "${HEALTH_CODE}",
    "prices": "${PRICES_CODE}",
    "news": "${NEWS_CODE}",
    "forecasts": "${FORECASTS_CODE}",
    "judge_quality": "${JUDGE_CODE}",
    "frontend_root": "${FRONT_CODE}"
  }
}
Path("${OUT_JSON}").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
print(f"result_file={Path('${OUT_JSON}')}")
PY

[[ "$STATUS" == "PASS" || "$DRY_RUN" -eq 1 ]]
