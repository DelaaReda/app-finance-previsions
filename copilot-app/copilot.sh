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
            "$SCRIPTS_DIR/start.sh" start
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