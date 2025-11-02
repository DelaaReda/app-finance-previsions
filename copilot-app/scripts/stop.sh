#!/bin/bash
#
# Script d'arrêt pour Finance Copilot

echo "🔄 Arrêt de Finance Copilot..."

# Tuer les processus backend
echo "🛑 Arrêt du backend..."
pkill -f "python.*run_api" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

# Tuer les processus frontend
echo "🛑 Arrêt du frontend..."
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Tuer les ports spécifiques
echo "🔌 Libération des ports..."
lsof -ti :8050 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

echo "✅ Finance Copilot a été arrêté."
echo "   Ports libérés: 8050 (backend), 5173 (frontend)"