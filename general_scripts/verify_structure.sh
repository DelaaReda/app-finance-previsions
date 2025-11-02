#!/bin/bash
#
# Script de vérification de la structure du projet Finance Copilot
# Vérifie que tous les fichiers sont au bon endroit et que rien n'a été créé à la racine

set -e

# Detect project directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
COPILOT_APP_DIR="$PROJECT_DIR/copilot-app"
AGENT_OSS_DIR="$PROJECT_DIR/agent-stack-oss"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Fonction pour vérifier la structure du projet
check_project_structure() {
    log "🔍 Vérification de la structure du projet..."
    
    # Vérifier que les dossiers principaux existent
    if [ ! -d "$COPILOT_APP_DIR" ]; then
        log_error "Dossier copilot-app manquant"
        return 1
    fi
    
    if [ ! -d "$AGENT_OSS_DIR" ]; then
        log_error "Dossier agent-stack-oss manquant"
        return 1
    fi
    
    # Vérifier la structure de copilot-app
    if [ ! -d "$COPILOT_APP_DIR/backend" ]; then
        log_error "Dossier copilot-app/backend manquant"
        return 1
    fi
    
    if [ ! -d "$COPILOT_APP_DIR/frontend" ]; then
        log_error "Dossier copilot-app/frontend manquant"
        return 1
    fi
    
    if [ ! -d "$COPILOT_APP_DIR/scripts" ]; then
        log_error "Dossier copilot-app/scripts manquant"
        return 1
    fi
    
    if [ ! -d "$COPILOT_APP_DIR/docs" ]; then
        log_error "Dossier copilot-app/docs manquant"
        return 1
    fi
    
    # Vérifier les fichiers essentiels
    if [ ! -f "$PROJECT_DIR/copilot.sh" ]; then
        log_error "Fichier copilot.sh manquant à la racine"
        return 1
    fi
    
    if [ ! -f "$PROJECT_DIR/README.md" ]; then
        log_error "Fichier README.md manquant à la racine"
        return 1
    fi
    
    if [ ! -f "$COPILOT_APP_DIR/scripts/start.sh" ]; then
        log_error "Fichier copilot-app/scripts/start.sh manquant"
        return 1
    fi
    
    if [ ! -f "$COPILOT_APP_DIR/scripts/stop.sh" ]; then
        log_error "Fichier copilot-app/scripts/stop.sh manquant"
        return 1
    fi
    
    if [ ! -f "$COPILOT_APP_DIR/docs/README_SCRIPTS.md" ]; then
        log_error "Fichier copilot-app/docs/README_SCRIPTS.md manquant"
        return 1
    fi
    
    log_success "Structure du projet correcte"
    return 0
}

# Fonction pour vérifier que rien n'a été créé à la racine
check_root_cleanliness() {
    log "🧹 Vérification de la propreté de la racine..."
    
    # Compter les fichiers à la racine (hors dossiers autorisés)
    ROOT_FILES_COUNT=$(find "$PROJECT_DIR" -maxdepth 1 -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.txt" -o -name "*.log" \) | wc -l | tr -d ' ')
    
    # Liste des fichiers autorisés à la racine
    AUTHORIZED_ROOT_FILES=(
        "copilot.sh"
        "README.md"
        ".gitignore"
        ".env.sample"
        "requirements.txt"
        "requirements-api.txt"
        "requirements-api-v2.txt"
        "Makefile"
        "AGENT_FILE_ORGANIZATION_GUIDE.md"
        "CLEANUP_PLAN.md"
        "verify_structure.sh"
    )
    
    UNAUTHORIZED_FILES=()
    
    # Vérifier chaque fichier à la racine
    for file in "$PROJECT_DIR"/*; do
        filename=$(basename "$file")
        
        # Ignorer les dossiers
        if [ -d "$file" ]; then
            continue
        fi
        
        # Vérifier si le fichier est autorisé
        is_authorized=false
        for authorized in "${AUTHORIZED_ROOT_FILES[@]}"; do
            if [ "$filename" = "$authorized" ]; then
                is_authorized=true
                break
            fi
        done
        
        # Si non autorisé, l'ajouter à la liste
        if [ "$is_authorized" = false ]; then
            UNAUTHORIZED_FILES+=("$filename")
        fi
    done
    
    if [ ${#UNAUTHORIZED_FILES[@]} -gt 0 ]; then
        log_warning "Fichiers non autorisés trouvés à la racine:"
        for file in "${UNAUTHORIZED_FILES[@]}"; do
            log_warning "  - $file"
        done
        return 1
    else
        log_success "Aucun fichier non autorisé trouvé à la racine"
        return 0
    fi
}

# Fonction pour vérifier que les scripts sont exécutables
check_scripts_executable() {
    log "⚙️  Vérification des permissions des scripts..."
    
    SCRIPTS_TO_CHECK=(
        "$PROJECT_DIR/copilot.sh"
        "$COPILOT_APP_DIR/scripts/start.sh"
        "$COPILOT_APP_DIR/scripts/stop.sh"
        "$COPILOT_APP_DIR/scripts/test_system.sh"
    )
    
    for script in "${SCRIPTS_TO_CHECK[@]}"; do
        if [ -f "$script" ]; then
            if [ ! -x "$script" ]; then
                log_warning "Script non exécutable: $script"
                log "  → Exécutez: chmod +x \"$script\""
                return 1
            fi
        else
            log_warning "Script manquant: $script"
            return 1
        fi
    done
    
    log_success "Tous les scripts sont exécutables"
    return 0
}

# Fonction pour vérifier l'état des services
check_services_status() {
    log "📊 Vérification de l'état des services..."
    
    # Vérifier si les services sont en cours d'exécution
    BACKEND_RUNNING=false
    FRONTEND_RUNNING=false
    
    if lsof -i :8050 >/dev/null 2>&1; then
        BACKEND_RUNNING=true
    fi
    
    if lsof -i :5173 >/dev/null 2>&1; then
        FRONTEND_RUNNING=true
    fi
    
    if [ "$BACKEND_RUNNING" = true ]; then
        log_success "Backend: EN COURS (port 8050)"
    else
        log_warning "Backend: ARRÊTÉ"
    fi
    
    if [ "$FRONTEND_RUNNING" = true ]; then
        log_success "Frontend: EN COURS (port 5173)"
    else
        log_warning "Frontend: ARRÊTÉ"
    fi
    
    return 0
}

# Fonction principale
main() {
    log "🚀 Vérification de la structure du projet Finance Copilot..."
    echo "================================================================"
    
    # Exécuter toutes les vérifications
    check_project_structure
    structure_result=$?
    
    check_root_cleanliness
    cleanliness_result=$?
    
    check_scripts_executable
    scripts_result=$?
    
    check_services_status
    services_result=$?
    
    echo "================================================================"
    
    # Afficher le résumé
    if [ $structure_result -eq 0 ] && [ $cleanliness_result -eq 0 ] && [ $scripts_result -eq 0 ]; then
        log_success "✅ Toutes les vérifications ont réussi !"
        echo ""
        echo "   📁 Structure du projet: CORRECTE"
        echo "   🧹 Propreté racine: RESPECTÉE"
        echo "   ⚙️  Permissions scripts: CORRECTES"
        echo ""
        echo "   🎯 Le projet est prêt à être utilisé !"
        return 0
    else
        log_error "❌ Certaines vérifications ont échoué !"
        echo ""
        echo "   📁 Structure du projet: $([ $structure_result -eq 0 ] && echo "✅ CORRECTE" || echo "❌ INCORRECTE")"
        echo "   🧹 Propreté racine: $([ $cleanliness_result -eq 0 ] && echo "✅ RESPECTÉE" || echo "❌ VIOLÉE")"
        echo "   ⚙️  Permissions scripts: $([ $scripts_result -eq 0 ] && echo "✅ CORRECTES" || echo "❌ INCORRECTES")"
        echo ""
        echo "   🛠️  Veuillez corriger les problèmes identifiés"
        return 1
    fi
}

# Exécuter la fonction principale
main "$@"