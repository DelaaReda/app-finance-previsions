#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT_DIR="$(readlink -f "$SCRIPT_DIR")"
if [[ "$SCRIPT_DIR" == */platform/policies ]]; then
  ROOT="${SCRIPT_DIR%/platform/policies}"
elif [[ "$SCRIPT_DIR" == */platform ]]; then
  ROOT="${SCRIPT_DIR%/platform}"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi

BACKEND_DIR="$ROOT/apps/api/src"
LIVE_CHECK=1
PYTEST_TARGETS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-live)
      LIVE_CHECK=0
      ;;
    --)
      shift
      PYTEST_TARGETS+=("$@")
      break
      ;;
    *)
      PYTEST_TARGETS+=("$1")
      ;;
  esac
  shift
done

if [[ ${#PYTEST_TARGETS[@]} -eq 0 ]]; then
  PYTEST_TARGETS=("domains/")
fi

check_endpoint() {
  local name="$1"
  local url="$2"
  local attempts="${3:-3}"
  local timeout="${4:-10}"

  local i
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time "$timeout" "$url" >/dev/null 2>&1; then
      echo "${name}=OK"
      return 0
    fi
    sleep 1
  done

  echo "${name}=FAIL"
  return 1
}

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "BLOCKED: backend directory not found: $BACKEND_DIR"
  exit 2
fi

if [[ -x "$BACKEND_DIR/.venv/bin/pytest" ]]; then
  PYTEST_BIN="$BACKEND_DIR/.venv/bin/pytest"
elif command -v pytest >/dev/null 2>&1; then
  PYTEST_BIN="$(command -v pytest)"
else
  echo "BLOCKED: pytest is not installed"
  exit 3
fi

echo "== BACKEND REGRESSION GATE =="
echo "backend_dir=$BACKEND_DIR"
echo "pytest_bin=$PYTEST_BIN"
echo "pytest_targets=${PYTEST_TARGETS[*]}"

pushd "$BACKEND_DIR" >/dev/null

PYTHONPATH_PREFIX="$ROOT:$BACKEND_DIR"
if [[ -n "${PYTHONPATH:-}" ]]; then
  PYTHONPATH_PREFIX="$PYTHONPATH_PREFIX:$PYTHONPATH"
fi

PYTHONPATH="$PYTHONPATH_PREFIX" "$PYTEST_BIN" -q "${PYTEST_TARGETS[@]}"

if [[ "$LIVE_CHECK" -eq 1 ]]; then
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS --max-time 5 "http://localhost:8050/api/health" >/dev/null 2>&1; then
      echo "health=UP"
      check_endpoint "stocks_prices" "http://localhost:8050/api/stocks/prices?ticker=AAPL&limit=2" 3 12
      check_endpoint "news_feed" "http://localhost:8050/api/news/feed?limit=1" 3 12
      echo "live_endpoints=OK"
    else
      echo "health=DOWN (live endpoint checks skipped)"
    fi
  fi
fi

popd >/dev/null
echo "VERDICT: PASS"
