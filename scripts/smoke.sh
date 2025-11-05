#!/usr/bin/env bash
# Smoke test script - verifies critical endpoints are responding properly
# Task: FC-P0-010 - Pre-push local: smoke hook
# Author: ALEX-FINANCE-ANALYST-SUPERMAN-29

set -euo pipefail

echo "🔍 Running smoke test..."

# Check if backend is running
if ! curl -sS http://localhost:8050/api/health > /dev/null 2>&1; then
    echo "❌ Backend not running on port 8050"
    echo "💡 Start with: /Users/venom/Documents/analyse-financiere/finance-copilot.sh start"
    exit 1
fi

# Test health endpoint
echo "🏥 Testing /api/health..."
if ! curl -sS http://localhost:8050/api/health | grep -qi ok > /dev/null; then
    echo "❌ Health check failed"
    exit 1
fi

# Test news endpoint
echo "📰 Testing /api/news/feed..."
if ! curl -sS http://localhost:8050/api/news/feed | jq -e '.data.articles // .articles' > /dev/null 2>&1; then
    echo "❌ News endpoint failed - missing articles key"
    exit 1
fi

# Test forecasts endpoint
echo "📈 Testing /api/forecasts..."
if ! curl -sS http://localhost:8050/api/forecasts | jq -e '.data.rows // .rows' > /dev/null 2>&1; then
    echo "❌ Forecasts endpoint failed - missing rows key"
    exit 1
fi

# Test brief endpoint
echo "📋 Testing /api/brief/weekly..."
if ! curl -sS http://localhost:8050/api/brief/weekly | head -c 80 > /dev/null; then
    echo "❌ Brief endpoint failed"
    exit 1
fi

# Test backtests endpoint
echo "📊 Testing /api/backtests..."
if ! curl -sS http://localhost:8050/api/backtests | head -c 80 > /dev/null; then
    echo "❌ Backtests endpoint failed"
    exit 1
fi

echo "✅ SMOKE TEST PASSED - All critical endpoints responding"
echo "✨ Ready to push safely"