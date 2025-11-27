#!/usr/bin/env bash
#
# Script optimisé pour Finance Copilot (ARM64/VM friendly)
# - Redémarre automatiquement si déjà en cours
# - Utilise le build frontend existant (pas de npm run dev)
# - Backend sans reload (évite segfault)
#

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $1"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')]${NC} $1"; }

# Chemins (résolution du répertoire réel du script)
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend/webapp"
FRONTEND_DIST="$FRONTEND_DIR/dist"

# Vérifier si un port est utilisé
is_port_in_use() {
    lsof -i ":$1" >/dev/null 2>&1
}

# Arrêter proprement les services
stop_services() {
    log "Arrêt des services existants..."
    
    # Arrêter backend
    pkill -f "python.*run_api.py" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    
    # Arrêter frontend
    pkill -f "http.server 5173" 2>/dev/null || true
    pkill -f "vite.*5173" 2>/dev/null || true
    
    # Nettoyer les PIDs
    rm -f /tmp/finance_copilot_*.pid
    
    sleep 2
    log_success "Services arrêtés"
}

# Générer les données initiales
generate_initial_data() {
    log "Génération des données initiales..."
    cd "$BACKEND_DIR"
    # Choisir l'interpréteur Python le plus fiable (éviter venv corrompue)
    PY=""
    if [ -x ".venv/bin/python3" ]; then
        PY=".venv/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PY="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PY="$(command -v python)"
    else
        log_error "Python introuvable (python3/python). Installez Python 3."
        exit 1
    fi
    # Lancer le job en arrière-plan
    nohup "$PY" jobs/validate_and_generate_data.py > /tmp/data_generation.log 2>&1 &
    DATA_GEN_PID=$!
    log_success "Job de génération lancé (PID: $DATA_GEN_PID)"
    log "Les données seront disponibles progressivement (voir /tmp/data_generation.log)"
}

# Rafraîchir les snapshots critiques (news, sentiment, judge_enrich, macro)
refresh_live_data() {
    log "Rafraîchissement des données (news, sentiment, judge_enrich, macro)..."
    cd "$BACKEND_DIR"

    PY=""
    if [ -x ".venv/bin/python3" ]; then
        PY=".venv/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PY="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PY="$(command -v python)"
    else
        log_error "Python introuvable (python3/python). Installez Python 3."
        exit 1
    }

    export PYTHONPATH="$BACKEND_DIR/src:$BACKEND_DIR"

    run_job() {
        local job="$1"
        log " → $job"
        if ! "$PY" "$job"; then
            log_warning "Job échoué: $job (on continue, pas de fallback silencieux)"
        fi
    }

    run_job "jobs/news_ingest.py"
    run_job "jobs/news_sentiment.py"
    run_job "jobs/judge_enrich.py"
    run_job "jobs/macro_series_snapshot.py"

    log_success "Rafraîchissement des données terminé."
}

# Démarrer le backend
start_backend() {
    log "Démarrage du backend..."
    
    cd "$BACKEND_DIR"
    # Désactiver reload pour éviter segfault sur ARM64
    export FINANCE_COPILOT_RELOAD=0
    # Prefer src/ first so 'api' resolves to src/api (contains services, schemas, etc.)
    export PYTHONPATH="$BACKEND_DIR/src:$BACKEND_DIR"
    # Choisir l'interpréteur Python (éviter venv si corrompue)
    PY=""
    if [ -x ".venv/bin/python3" ]; then
        PY=".venv/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PY="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PY="$(command -v python)"
    else
        log_error "Python introuvable (python3/python). Installez Python 3."
        exit 1
    fi
    
    # Démarrer en arrière-plan
    nohup "$PY" run_api.py > api.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/finance_copilot_backend.pid
    
    # Attendre que le backend réponde
    log "Attente du démarrage du backend..."
    for i in {1..15}; do
        if curl -fsS "http://localhost:8050/api/health" >/dev/null 2>&1; then
            log_success "✅ Backend opérationnel (PID: $BACKEND_PID)"
            log_success "   URL: http://localhost:8050"
            log_success "   Docs: http://localhost:8050/docs"
            return 0
        fi
        sleep 2
    done
    
    log_error "Le backend n'a pas démarré"
    tail -20 api.log
    exit 1
}

# Démarrer le frontend
start_frontend() {
    log "Démarrage du frontend..."
    
    # Vérifier si le build existe
    if [ ! -d "$FRONTEND_DIST" ]; then
        log_warning "Build frontend non trouvé, tentative de build..."
        cd "$FRONTEND_DIR"
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        npm run build || {
            log_error "Échec du build frontend"
            exit 1
        }
    fi
    
    # Servir le build avec Python (simple et rapide)
    cd "$FRONTEND_DIST"
    nohup python3 -m http.server 5173 > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/finance_copilot_frontend.pid
    
    # Attendre que le frontend réponde
    log "Attente du démarrage du frontend..."
    for i in {1..10}; do
        if curl -fsS "http://localhost:5173/" >/dev/null 2>&1; then
            log_success "✅ Frontend opérationnel (PID: $FRONTEND_PID)"
            log_success "   URL: http://localhost:5173"
            return 0
        fi
        sleep 1
    done
    
    log_error "Le frontend n'a pas démarré"
    tail -20 /tmp/frontend.log
    exit 1
}

# Afficher le statut
status() {
    echo ""
    echo "📊 État des services Finance Copilot"
    echo "======================================"
    
    if is_port_in_use 8050; then
        echo -e "${GREEN}✅ Backend${NC}  : EN COURS (http://localhost:8050)"
    else
        echo -e "${RED}❌ Backend${NC}  : ARRÊTÉ"
    fi
    
    if is_port_in_use 5173; then
        echo -e "${GREEN}✅ Frontend${NC} : EN COURS (http://localhost:5173)"
    else
        echo -e "${RED}❌ Frontend${NC} : ARRÊTÉ"
    fi
    
    echo ""
}

# Commande start (avec auto-restart si déjà en cours)
start() {
    log "Démarrage de Finance Copilot..."
    
    # Vérifier si déjà en cours
    if is_port_in_use 8050 || is_port_in_use 5173; then
        log_warning "Services déjà en cours, redémarrage..."
        stop_services
    fi
    
    # Générer les données en arrière-plan
    generate_initial_data

    # Rafraîchir les données live critiques (synchrones, pas de mock)
    refresh_live_data
    
    # Démarrer les services
    start_backend
    start_frontend
    
    echo ""
    log_success "🎉 Finance Copilot est opérationnel!"
    echo ""
    echo "🌐 URLs disponibles:"
    echo "   Frontend : http://localhost:5173"
    echo "   Backend  : http://localhost:8050"
    echo "   Docs API : http://localhost:8050/docs"
    echo ""
    echo "📝 Logs:"
    echo "   Backend  : $BACKEND_DIR/api.log"
    echo "   Frontend : /tmp/frontend.log"
    echo ""
}

# Afficher l'aide
show_help() {
    cat << EOF
Finance Copilot - Script optimisé (ARM64/VM)

Usage: $0 [commande]

Commandes:
  start    Démarre (ou redémarre) les services
  stop     Arrête tous les services
  restart  Redémarre tous les services
  status   Affiche l'état des services
  help     Affiche cette aide

URLs:
  Frontend : http://localhost:5173
  Backend  : http://localhost:8050
  Docs API : http://localhost:8050/docs

Note: Ce script optimisé utilise le build frontend existant
et désactive le reload du backend pour éviter les problèmes
sur architecture ARM64.
EOF
}

# Main
main() {
    case "${1:-help}" in
        start)
            start
            ;;
        stop)
            stop_services
            ;;
        restart)
            log "🔄 Redémarrage de Finance Copilot..."
            stop_services
            start
            ;;
        status)
            status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Commande inconnue: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
