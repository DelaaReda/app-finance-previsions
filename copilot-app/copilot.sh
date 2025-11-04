#!/usr/bin/env bash
#
# Script principal pour Finance Copilot
# Gestion centralisée des opérations de démarrage/arrêt

set -e

# Déterminer le répertoire réel du script (résout les liens symboliques)
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_DIR="$SCRIPT_DIR"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Vérifier que le dossier scripts existe
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "❌ Erreur: Dossier scripts introuvable dans $SCRIPT_DIR/scripts"
    exit 1
fi

# Fonction pour afficher l'aide
show_help() {
    echo "Finance Copilot - Script de gestion centralisée"
    echo ""
    echo "Usage: $0 [commande]"
    echo ""
    echo "Commandes:"
    echo "  start         Démarre le backend et le frontend"
    echo "  start-backend Démarrage backend seul avec PYTHONPATH"
    echo "  stop          Arrête tous les services"
    echo "  restart       Redémarre tous les services"
    echo "  status        Affiche l'état des services"
    echo "  test          Teste le système"
    echo "  help          Affiche cette aide"
    echo ""
    echo "URLs:"
    echo "  Frontend: http://localhost:5173"
    echo "  Backend:  http://localhost:8050"
    echo "  Docs API: http://localhost:8050/docs"
}

# Fonction pour démarrer le backend uniquement
start_backend_only() {
    echo "🚀 Démarrage du backend Finance Copilot..."
    
    # Déterminer le chemin correct du backend
    BACKEND_DIR="$PROJECT_DIR/backend"
    
    # Activer l'environnement virtuel
    if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
        source "$BACKEND_DIR/.venv/bin/activate"
    else
        echo "❌ Environnement virtuel backend non trouvé"
        exit 1
    fi
    
    # Exporter PYTHONPATH correctement
    export PYTHONPATH="$BACKEND_DIR/src"
    
    # Aller dans le répertoire backend et lancer uvicorn en arrière-plan
    cd "$BACKEND_DIR"
    nohup python run_api.py > api.log 2>&1 &
    BACKEND_PID=$!
    
    # Attendre que le backend démarre (wait loop - pas de timeout qui n'existe pas sur macOS)
    echo "⏳ Attente du démarrage du backend (10 tentatives)..."
    backend_up=0
    for i in {1..10}; do
        if curl -f -s "http://localhost:8050/api/health" >/dev/null 2>&1; then
            backend_up=1
            break
        fi
        sleep 2
        echo "   En attente du backend... ($i/10)"
    done
    
    # Vérifier si le backend répond
    if [ $backend_up -eq 1 ]; then
        echo $BACKEND_PID > /tmp/finance_copilot_backend.pid
        echo "✅ Backend démarré avec succès (PID: $BACKEND_PID)"
        echo "🌐 URL: http://localhost:8050"
    else
        echo "❌ Échec du démarrage du backend"
        tail -20 api.log
        exit 1
    fi
}

# Main
main() {
    case "${1:-help}" in
        start)
            echo "🚀 Démarrage de Finance Copilot..."
            "$SCRIPTS_DIR/start.sh" start
            ;;
        start-backend)
            start_backend_only
            ;;
        stop)
            echo "🛑 Arrêt de Finance Copilot..."
            "$SCRIPTS_DIR/stop.sh" stop
            ;;
        restart)
            echo "🔄 Redémarrage de Finance Copilot..."
            "$SCRIPTS_DIR/stop.sh" stop
            sleep 3
            "$SCRIPTS_DIR/start.sh" start
            ;;
        status)
            echo "📊 État des services Finance Copilot..."
            "$SCRIPTS_DIR/test_system.sh" test
            ;;
        test)
            echo "🧪 Test du système Finance Copilot..."
            "$SCRIPTS_DIR/test_system.sh" test
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "❌ Commande inconnue: $1"
            show_help
            exit 1
            ;;
    esac
}

# Exécuter la fonction principale
main "$@"