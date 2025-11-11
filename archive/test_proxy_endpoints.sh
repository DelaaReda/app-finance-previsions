#!/bin/bash
#
# Script de test des endpoints via proxy frontend
# Vérifie que tous les endpoints sont accessibles via le frontend proxy

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Test des endpoints via proxy frontend${NC}"
echo "=========================================="

SUCCESS=0
TOTAL=0

# Fonction pour tester un endpoint
test_endpoint() {
    local endpoint="$1"
    local expected_pattern="$2"
    local method="${3:-GET}"
    
    ((TOTAL++))
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s --max-time 15 "http://localhost:5173$endpoint" 2>/dev/null)
    elif [ "$method" = "POST" ]; then
        response=$(curl -s --max-time 15 -X POST "http://localhost:5173$endpoint" -H "Content-Type: application/json" -d '{}' 2>/dev/null)
    fi
    
    if [ $? -eq 0 ] && [ -n "$response" ] && echo "$response" | grep -q "$expected_pattern"; then
        echo -e "   ✅ $endpoint: OK"
        ((SUCCESS++))
    else
        echo -e "   ❌ $endpoint: ÉCHEC"
        echo "      Réponse: $response"
    fi
}

# Tester les endpoints critiques via le proxy frontend
echo -e "\n${YELLOW}Testing critical endpoints via frontend proxy...${NC}"

test_endpoint "/api/health" '"ok":true'
test_endpoint "/api/forecasts" '"ok":true'
test_endpoint "/api/brief/daily" '"ok":true'
test_endpoint "/api/brief/weekly" '"ok":true'
test_endpoint "/api/macro/series?ids=CPIAUCSL&limit=1" '"ok":true'
test_endpoint "/api/stocks/prices?ticker=SPY&range=1mo" '"ok":true'
test_endpoint "/api/news/feed?limit=5" '"ok":true'
test_endpoint "/api/dashboard/kpis" '"ok":true'

echo -e "\n${GREEN}📊 RÉSULTATS:${NC}"
echo "   $SUCCESS/$TOTAL endpoints fonctionnels"
echo ""

if [ $SUCCESS -eq $TOTAL ]; then
    echo -e "${GREEN}✅ Tous les tests ont réussi ! Le proxy frontend fonctionne correctement.${NC}"
    exit 0
else
    echo -e "${RED}❌ $((TOTAL - SUCCESS)) tests ont échoué. Vérifiez la configuration du proxy.${NC}"
    exit 1
fi