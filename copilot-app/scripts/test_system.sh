#!/bin/bash
#
# Script de test pour vérifier que Finance Copilot fonctionne correctement

echo "🧪 Test de Finance Copilot"
echo "==========================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher le statut
show_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ ÉCHEC${NC}"
    fi
}

# Test 1: Vérifier si les ports sont ouverts
echo "📡 Test des ports:"
echo "------------------"

# Backend
if lsof -i :8050 >/dev/null 2>&1; then
    echo -e "   Backend (8050): ${GREEN}EN COURS${NC}"
else
    echo -e "   Backend (8050): ${RED}ARRÊTÉ${NC}"
fi

# Frontend
if lsof -i :5173 >/dev/null 2>&1; then
    echo -e "   Frontend (5173): ${GREEN}EN COURS${NC}"
else
    echo -e "   Frontend (5173): ${RED}ARRÊTÉ${NC}"
fi

echo ""

# Test 2: Vérifier les endpoints backend
echo "🔍 Test des endpoints backend:"
echo "------------------------------"

# Health endpoint
echo -n "   /api/health: "
if curl -s "http://localhost:8050/api/health" | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ÉCHEC${NC}"
fi

# Brief endpoint
echo -n "   /api/brief/daily: "
if curl -s "http://localhost:8050/api/brief/daily" | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ÉCHEC${NC}"
fi

# Dashboard endpoint
echo -n "   /api/dashboard/kpis: "
if curl -s "http://localhost:8050/api/dashboard/kpis" | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ÉCHEC${NC}"
fi

# News feed endpoint (never-empty)
echo -n "   /api/news/feed: "
if curl -s "http://localhost:8050/api/news/feed" | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ÉCHEC${NC}"
fi

echo ""

# Test 3: Vérifier le frontend
echo "🖥️  Test du frontend:"
echo "--------------------"

# Accès à la page principale
echo -n "   Accès à http://localhost:5173: "
if curl -s "http://localhost:5173" | grep -q "<html"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ÉCHEC${NC}"
fi

echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJ_DIR/backend"
FRONTEND_DIR="$PROJ_DIR/frontend/webapp"

echo "📋 Vérification des logs:"
echo "------------------------"

# Backend logs
if [ -f "$BACKEND_DIR/api.log" ] && [ -s "$BACKEND_DIR/api.log" ]; then
    echo -e "   Backend logs: ${GREEN}PRÉSENTS ($(wc -l < "$BACKEND_DIR/api.log") lignes)${NC}"
else
    echo -e "   Backend logs: ${YELLOW}ABSENTS OU VIDES${NC}"
fi

# Frontend logs
if [ -f "$FRONTEND_DIR/frontend.log" ] && [ -s "$FRONTEND_DIR/frontend.log" ]; then
    echo -e "   Frontend logs: ${GREEN}PRÉSENTS ($(wc -l < "$FRONTEND_DIR/frontend.log") lignes)${NC}"
else
    echo -e "   Frontend logs: ${YELLOW}ABSENTS OU VIDES${NC}"
fi

echo ""

# Résumé
echo "📊 Résumé:"
echo "----------"

BACKEND_HEALTH=$(curl -s "http://localhost:8050/api/health" | grep -q '"ok":true' && echo 0 || echo 1)
FRONTEND_ACCESS=$(curl -s "http://localhost:5173" | grep -q "<html" && echo 0 || echo 1)
BRIEF_ENDPOINT=$(curl -s "http://localhost:8050/api/brief/daily" | grep -q '"ok":true' && echo 0 || echo 1)
NEWS_ENDPOINT=$(curl -s "http://localhost:8050/api/news/feed" | grep -q '"ok":true' && echo 0 || echo 1)

if [ $BACKEND_HEALTH -eq 0 ] && [ $FRONTEND_ACCESS -eq 0 ] && [ $BRIEF_ENDPOINT -eq 0 ] && [ $NEWS_ENDPOINT -eq 0 ]; then
    echo -e "${GREEN}🎉 Tous les tests ont réussi ! Finance Copilot est prêt à l'emploi.${NC}"
    echo ""
    echo "   🌐 URLs disponibles:"
    echo "      Frontend: http://localhost:5173"
    echo "      Backend:  http://localhost:8050"
    echo "      Docs API: http://localhost:8050/docs"
else
    echo -e "${YELLOW}⚠️  Certains tests ont échoué. Veuillez vérifier les services.${NC}"
fi
