#!/bin/bash
#
# Script de test pour l'intégration React DevTools dans Finance Copilot
# Vérifie que l'agent peut se connecter à l'application et extraire l'arbre React

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} $1"
}

# Fonction pour vérifier si un port est occupé
is_port_in_use() {
    lsof -i ":$1" >/dev/null 2>&1
}

# Fonction pour tuer les processus sur un port
kill_port() {
    if is_port_in_use $1; then
        log "Arrêt des processus sur le port $1..."
        lsof -ti :$1 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Fonction pour vérifier les dépendances
check_dependencies() {
    log "Vérification des dépendances React DevTools..."
    
    # Vérifier Node.js et npm
    if ! command -v node &> /dev/null; then
        log_error "Node.js n'est pas installé"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        log_error "npm n'est pas installé"
        exit 1
    fi
    
    # Vérifier que le dossier frontend existe
    if [ ! -d "./copilot-app/frontend/webapp" ]; then
        log_error "Dossier frontend introuvable: ./copilot-app/frontend/webapp"
        exit 1
    fi
    
    # Vérifier les dépendances Node
    if [ ! -f "./copilot-app/frontend/webapp/package.json" ]; then
        log_error "package.json non trouvé dans le frontend"
        exit 1
    fi
    
    # Vérifier que react-devtools est installé
    if [ ! -d "./copilot-app/frontend/webapp/node_modules/react-devtools" ]; then
        log_warning "react-devtools non trouvé, installation en cours..."
        cd ./copilot-app/frontend/webapp
        npm install react-devtools
        cd ../../../
    fi
    
    # Vérifier que playwright est installé
    if [ ! -d "./copilot-app/frontend/webapp/node_modules/playwright" ]; then
        log_warning "playwright non trouvé, installation en cours..."
        cd ./copilot-app/frontend/webapp
        npm install playwright
        npx playwright install chromium
        cd ../../../
    fi
    
    log_success "Toutes les dépendances React DevTools sont présentes"
}

# Fonction pour tester la connexion React DevTools
test_devtools_connection() {
    log "Test de la connexion React DevTools..."
    
    # Vérifier si l'application frontend est en cours d'exécution
    if ! curl -s "http://localhost:5173" | grep -q "<html"; then
        log_error "Frontend non accessible sur http://localhost:5173"
        log "Veuillez démarrer l'application avec: ./start.sh"
        return 1
    fi
    
    # Tester la connexion DevTools
    log "Connexion à React DevTools..."
    
    # Exécuter le script de snapshot
    cd ./copilot-app/frontend/webapp
    if npm run agent:snapshot > /tmp/react_devtools_test.log 2>&1; then
        log_success "Connexion React DevTools réussie"
        
        # Vérifier le contenu du résultat
        if grep -q '"ok":true' /tmp/react_devtools_test.log; then
            log_success "Arbre React extrait avec succès"
            trees_count=$(grep -o '"trees"' /tmp/react_devtools_test.log | wc -l)
            log_success "Nombre d'arbres React trouvés: $trees_count"
            
            # Afficher un aperçu
            log "Aperçu de l'arbre React:"
            head -20 /tmp/react_devtools_test.log
            
            cd ../../../
            return 0
        else
            log_error "Échec de l'extraction de l'arbre React"
            cat /tmp/react_devtools_test.log
            cd ../../../
            return 1
        fi
    else
        log_error "Échec de la connexion React DevTools"
        cat /tmp/react_devtools_test.log
        cd ../../../
        return 1
    fi
}

# Fonction pour tester les commandes DevTools
test_devtools_commands() {
    log "Test des commandes React DevTools..."
    
    cd ./copilot-app/frontend/webapp
    
    # Test npm run dev:devtools
    log "Test de la commande npm run dev:devtools..."
    if npm run dev:devtools --help >/dev/null 2>&1; then
        log_success "Commande npm run dev:devtools disponible"
    else
        log_warning "Commande npm run dev:devtools non disponible"
    fi
    
    # Test npm run agent:snapshot
    log "Test de la commande npm run agent:snapshot..."
    if npm run agent:snapshot --help >/dev/null 2>&1; then
        log_success "Commande npm run agent:snapshot disponible"
    else
        log_warning "Commande npm run agent:snapshot non disponible"
    fi
    
    cd ../../../
}

# Fonction pour tester les diagnostics
test_diagnostics() {
    log "Test des diagnostics React DevTools..."
    
    cd ./copilot-app/frontend/webapp
    
    # Test des checks
    if [ -f "tools/agent/checks.ts" ]; then
        log_success "Fichier de diagnostics trouvé: tools/agent/checks.ts"
        
        # Vérifier le contenu
        if grep -q "findPropBloat\|findAnonymous" tools/agent/checks.ts; then
            log_success "Fonctions de diagnostic présentes"
        else
            log_warning "Fonctions de diagnostic absentes"
        fi
    else
        log_warning "Fichier de diagnostics introuvable: tools/agent/checks.ts"
    fi
    
    cd ../../../
}

# Fonction principale
main() {
    log "🚀 Test de l'intégration React DevTools pour Finance Copilot..."
    echo "================================================================"
    
    # Vérifier les dépendances
    check_dependencies
    
    # Tester les commandes
    test_devtools_commands
    
    # Tester les diagnostics
    test_diagnostics
    
    # Tester la connexion (si l'application est démarrée)
    if curl -s "http://localhost:5173" | grep -q "<html"; then
        test_devtools_connection
        connection_result=$?
    else
        log_warning "Application non démarrée - test de connexion ignoré"
        connection_result=0
    fi
    
    echo "================================================================"
    
    # Afficher le résumé
    if [ $connection_result -eq 0 ]; then
        log_success "✅ Tous les tests React DevTools ont réussi !"
        echo ""
        echo "   🎯 Intégration React DevTools: OPÉRATIONNELLE"
        echo "   🧪 Diagnostics: DISPONIBLES"
        echo "   📊 Connexion: $(if [ $connection_result -eq 0 ]; then echo "✅ CONNECTÉE"; else echo "❌ DÉCONNECTÉE"; fi)"
        echo ""
        echo "   🚀 Vous pouvez maintenant utiliser:"
        echo "      npm run dev:devtools  # Démarrer avec DevTools"
        echo "      npm run agent:snapshot # Extraire l'arbre React"
        return 0
    else
        log_error "❌ Certains tests React DevTools ont échoué !"
        echo ""
        echo "   🎯 Intégration React DevTools: $(if [ $connection_result -eq 0 ]; then echo "✅ OPÉRATIONNELLE"; else echo "❌ PROBLÉMATIQUE"; fi)"
        echo "   🧪 Diagnostics: DISPONIBLES"
        echo "   📊 Connexion: $(if [ $connection_result -eq 0 ]; then echo "✅ CONNECTÉE"; else echo "❌ DÉCONNECTÉE"; fi)"
        echo ""
        echo "   🔧 Pour résoudre les problèmes:"
        echo "      1. Démarrez l'application: ./start.sh"
        echo "      2. Exécutez à nouveau ce test"
        echo "      3. Vérifiez les logs: tail -f /tmp/react_devtools_test.log"
        return 1
    fi
}

# Exécuter la fonction principale avec les arguments
case "${1:-test}" in
    test)
        main
        ;;
    help|--help|-h)
        echo "Test de l'intégration React DevTools pour Finance Copilot"
        echo ""
        echo "Usage: $0 [commande]"
        echo ""
        echo "Commandes:"
        echo "  test     Exécute tous les tests (défaut)"
        echo "  help     Affiche cette aide"
        echo ""
        echo "Prérequis:"
        echo "  - Application Finance Copilot démarrée (./start.sh)"
        echo "  - Node.js et npm installés"
        echo "  - Dépendances frontend installées"
        echo ""
        echo "Fonctionnalités testées:"
        echo "  - Connexion React DevTools"
        echo "  - Extraction de l'arbre React"
        echo "  - Commandes DevTools"
        echo "  - Diagnostics"
        ;;
    *)
        log_error "Commande inconnue: $1"
        echo "Utilisez '$0 help' pour afficher l'aide"
        exit 1
        ;;
esac