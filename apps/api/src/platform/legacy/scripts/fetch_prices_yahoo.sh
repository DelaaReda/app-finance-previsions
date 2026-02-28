#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$BACKEND_DIR/data/price_cache/yahoo"
mkdir -p "$OUT_DIR"

DEFAULT_TICKERS=(
  SPY QQQ AAPL MSFT GOOGL AMZN NVDA META TSLA
  BRK.B UNH JNJ V PG JPM MA HD DIS
)

TICKERS=("${DEFAULT_TICKERS[@]}")
START_DATE=""
END_DATE=""
INTERVAL="1d"
EVENTS="history"
COOKIE_FILE=""

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --tickers "SPY,QQQ,AAPL"   Comma-separated tickers (default: common universe)
  --start   YYYY-MM-DD       Start date (default: 1 year ago)
  --end     YYYY-MM-DD       End date (default: today)
  --interval 1d|1wk|1mo      Interval (default: 1d)
  --events  history|div|split  Events (default: history)
  --cookie  /path/cookies.txt  Netscape cookie file (optional; helps if Gold required)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tickers)
      IFS=',' read -r -a TICKERS <<< "${2:-}"
      shift 2
      ;;
    --start)
      START_DATE="${2:-}"
      shift 2
      ;;
    --end)
      END_DATE="${2:-}"
      shift 2
      ;;
    --interval)
      INTERVAL="${2:-1d}"
      shift 2
      ;;
    --events)
      EVENTS="${2:-history}"
      shift 2
      ;;
    --cookie)
      COOKIE_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for date conversion." >&2
  exit 1
fi

if [[ -z "$COOKIE_FILE" ]]; then
  COOKIE_FILE="$(mktemp)"
  CLEAN_COOKIE=1
else
  CLEAN_COOKIE=0
fi

cleanup() {
  if [[ "${CLEAN_COOKIE}" -eq 1 ]]; then
    rm -f "$COOKIE_FILE"
  fi
}
trap cleanup EXIT

date_to_epoch() {
  python3 - "$1" <<'PY'
from datetime import datetime, timezone
import sys
s = sys.argv[1].strip()
dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
print(int(dt.timestamp()))
PY
}

if [[ -z "$END_DATE" ]]; then
  END_DATE="$(python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
PY
)"
fi

if [[ -z "$START_DATE" ]]; then
  START_DATE="$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d"))
PY
)"
fi

PERIOD1="$(date_to_epoch "$START_DATE")"
PERIOD2="$(date_to_epoch "$END_DATE")"

echo "Yahoo historical download:"
echo "  start=$START_DATE end=$END_DATE interval=$INTERVAL events=$EVENTS"

fetch_crumb() {
  local c
  c="$(curl -s -L -c "$COOKIE_FILE" 'https://query1.finance.yahoo.com/v1/test/getcrumb' || true)"
  if [[ -n "$c" ]]; then
    echo "$c"
    return
  fi
  c="$(curl -s -L -c "$COOKIE_FILE" 'https://query2.finance.yahoo.com/v1/test/getcrumb' || true)"
  if [[ -n "$c" ]]; then
    echo "$c"
    return
  fi
  echo ""
}

# Get crumb (may require subscription login)
CRUMB="$(fetch_crumb)"
if [[ -z "$CRUMB" ]]; then
  # Try parsing from quote history page
  FIRST="${TICKERS[0]}"
  HTML="$(curl -s -L -c "$COOKIE_FILE" -b "$COOKIE_FILE" "https://finance.yahoo.com/quote/${FIRST}/history?p=${FIRST}" || true)"
  if [[ -n "$HTML" ]]; then
    CRUMB="$(echo "$HTML" | sed -n 's/.*"CrumbStore":{"crumb":"\\([^"]*\\)".*/\\1/p' | head -n 1 | sed 's|\\\\u002F|/|g')"
  fi
fi

if [[ -z "$CRUMB" ]]; then
  echo "Could not fetch Yahoo crumb. If you have Gold, export a cookie file and pass --cookie." >&2
  exit 2
fi

for T in "${TICKERS[@]}"; do
  OUT="$OUT_DIR/${T}.csv"
  URL="https://query1.finance.yahoo.com/v7/finance/download/${T}?period1=${PERIOD1}&period2=${PERIOD2}&interval=${INTERVAL}&events=${EVENTS}&includeAdjustedClose=true&crumb=${CRUMB}"
  if curl -sS -b "$COOKIE_FILE" "$URL" -o "$OUT"; then
    if grep -qi '^date' "$OUT"; then
      echo "  ✓ $T"
    else
      echo "  ! $T (downloaded but not CSV; check Gold access/cookies)" >&2
      rm -f "$OUT"
    fi
  else
    echo "  ! $T (download failed)" >&2
    rm -f "$OUT"
  fi
done

echo "Done. Output: $OUT_DIR"
