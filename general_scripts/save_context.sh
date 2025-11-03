#!/bin/bash
#
# Script de sauvegarde du contexte du projet Finance Copilot
# Exporte l'état actuel du projet pour reprise ultérieure

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

# Fonction pour obtenir l'état des services
get_service_status() {
    local port=$1
    local service_name=$2
    
    if lsof -i ":$port" >/dev/null 2>&1; then
        echo "✅ $service_name: EN COURS (port $port)"
    else
        echo "❌ $service_name: ARRÊTÉ"
    fi
}

# Fonction pour tester les endpoints API
test_api_endpoints() {
    log "Test des endpoints API..."
    
    local endpoints=(
        "/api/health"
        "/api/freshness"
        "/api/macro/series?ids=CPIAUCSL&limit=1"
        "/api/macro/snapshot"
        "/api/macro/indicators"
        "/api/stocks/prices?ticker=SPY&range=1mo"
        "/api/stocks/universe"
        "/api/news/feed?limit=5"
        "/api/news/sentiment"
        "/api/news/events"
        "/api/brief/daily"
        "/api/brief/weekly"
        "/api/dashboard/kpis"
    )
    
    local working=0
    local total=${#endpoints[@]}
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s --max-time 10 "http://localhost:8050$endpoint" | grep -q '"ok":true'; then
            echo "   ✅ $endpoint: OK"
            ((working++))
        else
            echo "   ❌ $endpoint: ÉCHEC"
        fi
    done
    
    echo "Endpoints fonctionnels: $working/$total"
}

# Fonction pour obtenir la structure du projet
get_project_structure() {
    log "Structure du projet..."
    
    # Obtenir la structure des dossiers principaux
    find . -maxdepth 3 -type d | grep -E "(copilot-app|agent-stack-oss)" | sort
}

# Fonction pour obtenir les processus actifs
get_active_processes() {
    log "Processus actifs..."
    
    # Processus backend
    ps aux | grep -E "(python.*run_api|uvicorn)" | grep -v grep || echo "   Aucun processus backend trouvé"
    
    # Processus frontend
    ps aux | grep -E "(npm.*dev|vite)" | grep -v grep || echo "   Aucun processus frontend trouvé"
}

# Fonction pour obtenir les statistiques des fichiers
get_file_stats() {
    log "Statistiques des fichiers..."
    
    echo "   Fichiers Python: $(find . -name "*.py" | wc -l)"
    echo "   Fichiers TypeScript: $(find . -name "*.ts" -o -name "*.tsx" | wc -l)"
    echo "   Fichiers Markdown: $(find . -name "*.md" | wc -l)"
    echo "   Fichiers de configuration: $(find . -name "*.json" -o -name "*.yaml" -o -name "*.yml" | wc -l)"
}

# Fonction principale de sauvegarde du contexte
save_context() {
    local output_file="${1:-CONTEXT_EXPORT_$(date +%Y%m%d_%H%M%S).md}"
    
    log "Sauvegarde du contexte dans $output_file..."
    
    # Obtenir les informations dynamiques
    local timestamp=$(date +"%d/%m/%Y à %H:%M")
    local structure=$(find . -maxdepth 3 -type d | grep -E "(copilot-app|agent-stack-oss)" | sort | sed 's/^/├── /')
    local backend_status=$(get_service_status 8050 "Backend API")
    local frontend_status=$(get_service_status 5173 "Frontend UI")
    local active_processes=$(get_active_processes)
    local file_stats=$(get_file_stats)
    local api_status=$(test_api_endpoints)
    
    # Créer le fichier de contexte avec les données réelles
    cat > "$output_file" << EOF
# 📋 CONTEXTE ACTUEL DU PROJET FINANCE COPILOT
# Exporté le: $timestamp
# Par: Script de sauvegarde automatique

## 🎯 ÉTAT ACTUEL DU PROJET

### Structure actuelle
\`\`\`
$structure
\`\`\`

## 🚀 SERVICES ACTIFS

### État des services
$backend_status
$frontend_status

## 🔧 PROCESSUS ACTIFS

$active_processes

## 📊 STATISTIQUES DU PROJET

$file_stats

## 🧪 ÉTAT DES ENDPOINTS API

$api_status

## 📝 NOTES

- Dernière sauvegarde effectuée le $timestamp
- Pour restaurer ce contexte, suivez les instructions ci-dessous

## 🔄 INSTRUCTIONS DE RESTAURATION

1. Vérifier que tous les services sont arrêtés: \`./stop.sh\`
2. Vérifier la structure des dossiers
3. Restaurer les fichiers de configuration si nécessaire
4. Démarrer les services: \`./start.sh\`
5. Vérifier l'état: \`./test_system.sh\`

---
Exporté automatiquement par le script de sauvegarde le $timestamp
EOF
    
    log_success "Contexte sauvegardé dans $output_file"
}

# Fonction pour afficher l'aide
show_help() {
    echo "Sauvegarde du contexte du projet Finance Copilot"
    echo ""
    echo "Usage: $0 [nom_fichier]"
    echo ""
    echo "Arguments:"
    echo "  nom_fichier    Nom du fichier de sortie (optionnel)"
    echo "                 Par défaut: CONTEXT_EXPORT_YYYYMMDD_HHMMSS.md"
    echo ""
    echo "Exemples:"
    echo "  $0                          # Sauvegarde avec nom par défaut"
    echo "  $0 context_actuel.md        # Sauvegarde dans context_actuel.md"
    echo ""
    echo "Fonctionnalités:"
    echo "  - Exporte l'état actuel du projet"
    echo "  - Inclut la structure des dossiers"
    echo "  - Teste les services actifs"
    echo "  - Vérifie les endpoints API"
    echo "  - Documente les processus en cours"
}

# Main
main() {
    case "${1:-}" in
        help|--help|-h)
            show_help
            ;;
        "")
            save_context
            ;;
        *)
            save_context "$1"
            ;;
    esac
}

# Exécuter la fonction principale
main "$@"