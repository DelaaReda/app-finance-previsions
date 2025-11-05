#!/usr/bin/env bash
# scripts/smoke.sh
# Smoke test for Finance Copilot - checks critical endpoints without using 'timeout'
set -euo pipefail

echo " smoke test: checking backend health..."

# Test 1: Health endpoint
if ! curl -fsS http://localhost:8050/api/health | grep -q '"ok": true'; then
    echo "❌ SMOKE FAIL: /api/health not responding correctly"
    exit 1
fi
echo "✅ /api/health OK"

# Test 2: News feed endpoint - check if articles key exists in data
if ! curl -fsS http://localhost:8050/api/news/feed 2>/dev/null | grep -q '"articles"'; then
    echo "❌ SMOKE FAIL: /api/news/feed missing articles key"
    exit 1
fi
echo "✅ /api/news/feed OK"

# Test 3: Forecasts endpoint - check if rows key exists in data
if ! curl -fsS http://localhost:8050/api/forecasts 2>/dev/null | grep -q '"rows"'; then
    echo "❌ SMOKE FAIL: /api/forecasts missing rows key"
    exit 1
fi
echo "✅ /api/forecasts OK"

# Test 4: Brief/weekly endpoint - check if it responds with valid JSON containing ok
if ! curl -fsS http://localhost:8050/api/brief/weekly 2>/dev/null | grep -q '"ok"'; then
    echo "❌ SMOKE FAIL: /api/brief/weekly not responding properly"
    exit 1
fi
echo "✅ /api/brief/weekly OK"

# Test 5: Backtests endpoint - check if it responds with valid JSON containing ok
if ! curl -fsS http://localhost:8050/api/backtests 2>/dev/null | grep -q '"ok"'; then
    echo "❌ SMOKE FAIL: /api/backtests not responding properly"
    exit 1
fi
echo "✅ /api/backtests OK"

echo "SMOKE OK - All critical endpoints responding"