#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$BACKEND_DIR/data/price_cache/stooq"

mkdir -p "$OUT_DIR"

TICKERS=(
  SPY QQQ AAPL MSFT GOOGL AMZN NVDA META TSLA
  BRK.B UNH JNJ V PG JPM MA HD DIS
)

echo "Fetching prices from stooq.pl..."
for T in "${TICKERS[@]}"; do
  sym="$(echo "$T" | tr '[:upper:]' '[:lower:]')"
  tmp="$OUT_DIR/${T}.csv.tmp"
  out="$OUT_DIR/${T}.csv"

  # Try direct stooq.pl first, then jina.ai mirror
  if curl -sS "https://stooq.pl/q/d/l/?s=${sym}.us&i=d" > "$tmp"; then
    true
  else
    rm -f "$tmp"
  fi

  if [ ! -s "$tmp" ]; then
    if curl -sS "https://r.jina.ai/http://stooq.pl/q/d/l/?s=${sym}.us&i=d" \
      | awk 'BEGIN{found=0} /^Markdown Content:/{found=1; next} {if(found) print}' \
      | sed '1s/^Data,Otwarcie,Najwyzszy,Najnizszy,Zamkniecie,Wolumen/Date,Open,High,Low,Close,Volume/' \
      > "$tmp"; then
      true
    else
      rm -f "$tmp"
    fi
  fi

  if [ -s "$tmp" ]; then
    if [ -s "$tmp" ]; then
      mv "$tmp" "$out"
      echo "  ✓ $T"
    else
      rm -f "$tmp"
      echo "  ! $T (empty)" >&2
    fi
  else
    rm -f "$tmp"
    echo "  ! $T (fetch failed)" >&2
  fi
done

echo "Done. Output: $OUT_DIR"
