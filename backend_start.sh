#!/bin/bash
#
# Script de démarrage backend pour Finance Copilot
# Lance le serveur uvicorn et attend qu'il soit prêt avec une boucle d'attente
# (sans utiliser la commande `timeout` qui n'est pas disponible sur macOS)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$(cd "$PROJECT_DIR/copilot-app/backend" && pwd)"

# Charger l'environnement si disponible
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

# Activer l'environnement virtuel
if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    source "$BACKEND_DIR/.venv/bin/activate"
else
    echo "❌ Environnement virtuel non trouvé: $BACKEND_DIR/.venv/bin/activate"
    exit 1
fi

# Vérifier que le script Python existe
if [ ! -f "$BACKEND_DIR/run_api.py" ]; then
    echo "❌ Fichier run_api.py non trouvé dans: $BACKEND_DIR"
    exit 1
fi

# Exporter PYTHONPATH comme demandé
export PYTHONPATH="$(pwd)/copilot-app/backend"

echo "🚀 Démarrage du backend Finance Copilot..."
echo "   Backend dir: $BACKEND_DIR"
echo "   PYTHONPATH: $PYTHONPATH"

# Tuer les processus existants sur le port 8050
if lsof -i :8050 >/dev/null 2>&1; then
    echo "🔒 Port 8050 occupé, arrêt des processus existants..."
    lsof -ti :8050 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Lancer uvicorn en arrière-plan
echo "🎬 Lancement du serveur uvicorn..."
cd "$BACKEND_DIR"
nohup python run_api.py > backend.log 2>&1 &
BACKEND_PID=$!

# Attendre que le backend démarre (wait loop - pas de timeout qui n'existe pas sur macOS)
echo "⏳ Attente du démarrage du backend (10 tentatives, 2s d'intervalle)..."
backend_up=0
for i in {1..10}; do
    if curl -sf "http://localhost:8050/api/health" >/dev/null 2>&1; then
        backend_up=1
        break
    fi
    sleep 2
    echo "   En attente du backend... tentative $i/10"
done

# Écrire le PID dans un fichier
if [ $backend_up -eq 1 ]; then
    echo $BACKEND_PID > /tmp/finance_copilot_backend.pid
    echo "✅ Backend démarré avec succès (PID: $BACKEND_PID)"
    echo "🌐 URL: http://localhost:8050"
    
    # Afficher les dernières lignes du log pour debug
    echo "📄 Dernières lignes du log:"
    tail -5 backend.log
else
    echo "❌ Échec du démarrage du backend après 10 tentatives"
    echo "📄 Contenu du log pour diagnostic:"
    cat backend.log
    exit 1
fi