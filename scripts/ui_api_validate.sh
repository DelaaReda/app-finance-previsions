#!/usr/bin/env bash
set -euo pipefail

API=${API_BASE:-http://localhost:8050}
OUT_DIR="proofs/FC-UI-VALIDATION"
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT_DIR"

echo "[ui_api_validate] API=$API TS=$TS"

check(){
  local name="$1"; shift
  local url="$1"; shift
  echo "-- $name ($url)" | tee -a "$OUT_DIR/$TS.log"
  # save full json
  curl -sS "$url" > "$OUT_DIR/${TS}_${name}.json" || true
  # minimal structure report
  if command -v jq >/dev/null 2>&1; then
    jq '{ok, data_type: (.data|type), keys: (.data|keys?)}' "$OUT_DIR/${TS}_${name}.json" 2>/dev/null | tee -a "$OUT_DIR/$TS.log" || tail -c 400 "$OUT_DIR/${TS}_${name}.json" | tee -a "$OUT_DIR/$TS.log"
  else
    head -c 400 "$OUT_DIR/${TS}_${name}.json" | tee -a "$OUT_DIR/$TS.log"
  fi
  echo "" | tee -a "$OUT_DIR/$TS.log"
}

check "kpis"        "$API/api/dashboard/kpis?horizons=short"
check "brief_daily" "$API/api/brief/daily"
check "brief_weekly" "$API/api/brief/weekly"
check "backtests"   "$API/api/backtests?horizon=1m&top_n=5&days_back=180"
check "forecasts"   "$API/api/forecasts"
check "news_feed"   "$API/api/news/feed?limit=5"
check "stocks_aapl" "$API/api/stocks/AAPL"
check "macro_series" "$API/api/macro/series?ids=CPIAUCSL,VIXCLS,T10Y2Y"

echo "[ui_api_validate] Done. Report: $OUT_DIR/$TS.log"

