#!/bin/bash
# Script de test pour vérifier les performances des endpoints et l'UI
# Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77

echo "🔍 Test de Performance UI - Finance Copilot"
echo "=============================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_URL="http://localhost:8050"
FRONTEND_URL="http://localhost:5173"

# Fonction pour tester un endpoint
test_endpoint() {
    local endpoint=$1
    local name=$2
    local max_time=${3:-5}
    
    echo -n "Testing $name... "
    start_time=$(date +%s.%N)
    
    response=$(timeout $max_time curl -s -w "\n%{http_code}" "$BACKEND_URL$endpoint" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    
    if [ "$http_code" = "200" ]; then
        # Vérifier si la réponse contient des données
        if echo "$body" | grep -q '"data"'; then
            echo -e "${GREEN}✅ OK${NC} (${duration}s) - Data present"
        else
            echo -e "${YELLOW}⚠️  OK${NC} (${duration}s) - Empty structure"
        fi
    else
        echo -e "${RED}❌ FAILED${NC} (HTTP $http_code)"
    fi
}

# Test des endpoints
echo "📊 Testing Backend Endpoints..."
echo ""

test_endpoint "/api/health" "Health Check" 2
test_endpoint "/api/dashboard/kpis" "Dashboard KPIs" 5
test_endpoint "/api/correlations/matrix" "Correlation Matrix" 5
test_endpoint "/api/correlations/network?threshold=0.5" "Correlation Network" 5
test_endpoint "/api/stocks/sectors" "Sectors" 5
test_endpoint "/api/backtests/efficient_frontier" "Efficient Frontier" 5
test_endpoint "/api/flows/capital" "Capital Flows" 5
test_endpoint "/api/orderbook?ticker=AAPL" "OrderBook" 5

echo ""
echo "🌐 Testing Frontend..."
echo ""

if timeout 2 curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is running${NC}"
else
    echo -e "${RED}❌ Frontend is not responding${NC}"
fi

echo ""
echo "📈 Performance Summary"
echo "======================"
echo "All endpoints should respond in < 5 seconds"
echo "If endpoints are slow, check:"
echo "  - Backend logs for errors"
echo "  - Database/storage performance"
echo "  - Network latency"
echo "  - Cache configuration in hooks"

