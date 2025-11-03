#!/bin/bash
#
# Script de démarrage principal pour Finance Copilot
# Pointe vers les scripts dans le dossier copilot-app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COPILOT_APP_DIR="$SCRIPT_DIR/copilot-app"

# Vérifier que le dossier copilot-app existe
if [ ! -d "$COPILOT_APP_DIR" ]; then
    echo "❌ Erreur: Dossier copilot-app introuvable"
    exit 1
fi

# Fonction pour afficher l'aide
show_help() {
    echo "Finance Copilot - Script de démarrage principal"
    echo ""
    echo "Usage: $0 [commande]"
    echo ""
    echo "Commandes:"
    echo "  start     Démarre le backend et le frontend"
    echo "  stop      Arrête tous les services"
    echo "  restart   Redémarre tous les services"
    echo "  status    Affiche l'état des services"
    echo "  test      Teste le système"
    echo "  help      Affiche cette aide"
    echo ""
    echo "URLs:"
    echo "  Frontend: http://localhost:5173"
    echo "  Backend:  http://localhost:8050"
    echo "  Docs API: http://localhost:8050/docs"
}

# Main
main() {
    case "${1:-help}" in
        start)
            echo "🚀 Démarrage de Finance Copilot..."
            "$COPILOT_APP_DIR/scripts/start.sh"
            ;;
        stop)
            echo "🛑 Arrêt de Finance Copilot..."
            "$COPILOT_APP_DIR/scripts/stop.sh"
            ;;
        restart)
            echo "🔄 Redémarrage de Finance Copilot..."
            "$COPILOT_APP_DIR/scripts/stop.sh"
            sleep 3
            "$COPILOT_APP_DIR/scripts/start.sh"
            ;;
        status)
            echo "📊 État des services Finance Copilot..."
            "$COPILOT_APP_DIR/scripts/test_system.sh"
            ;;
        test)
            echo "🧪 Test du système Finance Copilot..."
            "$COPILOT_APP_DIR/scripts/test_system.sh"
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