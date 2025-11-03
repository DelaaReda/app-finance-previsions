#!/usr/bin/env bash
set -euo pipefail

# Run all agents (parallel where safe), then restart Dash
# Usage: AF_DASH_PORT=8050 bash scripts/refresh_all_and_restart.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/src"

echo "[refresh-all] Starting parallel agents..."

# Group A (parallel): backfill prices, news harvester, macro forecast, equity forecast, commodity forecast
( make backfill-prices >/dev/null 2>&1 && echo "[refresh-all] backfill-prices: OK" || echo "[refresh-all] backfill-prices: WARN" ) &
( make harvester-once   >/dev/null 2>&1 && echo "[refresh-all] harvester-once: OK"   || echo "[refresh-all] harvester-once: WARN" ) &
( make macro-forecast   >/dev/null 2>&1 && echo "[refresh-all] macro-forecast: OK"   || echo "[refresh-all] macro-forecast: WARN" ) &
( make equity-forecast  >/dev/null 2>&1 && echo "[refresh-all] equity-forecast: OK"  || echo "[refresh-all] equity-forecast: WARN" ) &
( make commodity-forecast >/dev/null 2>&1 && echo "[refresh-all] commodity-forecast: OK" || echo "[refresh-all] commodity-forecast: WARN" ) &

wait || true

# LLM context + forecast
echo "[refresh-all] Building LLM contexts..."
make llm-context >/dev/null 2>&1 && echo "[refresh-all] llm-context: OK" || echo "[refresh-all] llm-context: WARN"
echo "[refresh-all] Running LLM forecast..."
make llm-forecast >/dev/null 2>&1 && echo "[refresh-all] llm-forecast: OK" || echo "[refresh-all] llm-forecast: WARN"

echo "[refresh-all] Aggregating forecasts..."
make forecast-aggregate || true

echo "[refresh-all] Running backtests & evaluation (parallel)..."
( make backtest  >/dev/null 2>&1 && echo "[refresh-all] backtest: OK"  || echo "[refresh-all] backtest: WARN" ) &
( make evaluate  >/dev/null 2>&1 && echo "[refresh-all] evaluate: OK"  || echo "[refresh-all] evaluate: WARN" ) &
wait || true

echo "[refresh-all] Updating freshness monitor..."
make update-monitor || true

echo "[refresh-all] Restarting Dash..."
bash scripts/dash_restart_bg.sh

echo "[refresh-all] Done. Open http://localhost:${AF_DASH_PORT:-8050}"
