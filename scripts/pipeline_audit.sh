#!/usr/bin/env bash
set -euo pipefail

API=${API_BASE:-http://localhost:8050}
OUT_DIR="proofs/FC-DATA-ANALYSIS"
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT_DIR"

echo "[pipeline_audit] API=$API TS=$TS"

dump(){
  local name="$1"; shift
  local url="$1"; shift
  curl -sS "$url" > "$OUT_DIR/${TS}_${name}.json" || true
}

dump health        "$API/api/health"
dump kpis          "$API/api/dashboard/kpis?horizons=short"
dump brief_daily   "$API/api/brief/daily"
dump backtests     "$API/api/backtests?horizon=1m&top_n=5&days_back=180"
dump forecasts     "$API/api/forecasts"
dump news_feed     "$API/api/news/feed?limit=100"
dump macro_series  "$API/api/macro/series?ids=CPIAUCSL,VIXCLS,T10Y2Y"
dump stocks_aapl   "$API/api/stocks/AAPL"

if command -v jq >/dev/null 2>&1; then
  jq '{ok, last_updates, news_stats, status}' "$OUT_DIR/${TS}_health.json" 2>/dev/null > "$OUT_DIR/${TS}_health_summary.json" || true
  jq '{ok, count: (.data.count // (.data.articles|length) // 0), freshness: (.data.freshness // .data.last_update)}' "$OUT_DIR/${TS}_news_feed.json" 2>/dev/null > "$OUT_DIR/${TS}_news_summary.json" || true
  jq '{ok, count: (.data.count // 0)}' "$OUT_DIR/${TS}_forecasts.json" 2>/dev/null > "$OUT_DIR/${TS}_forecasts_summary.json" || true
fi

echo "[pipeline_audit] Snapshots saved to $OUT_DIR"

