#!/bin/bash
#
# Script de démarrage complet pour Finance Copilot
# Démarre le backend et le frontend automatiquement

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project dir is the copilot-app root
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend/webapp"
ENV_FILE="$PROJECT_DIR/.env"

# Ensure backend src on PYTHONPATH for standalone jobs
export PYTHONPATH="$BACKEND_DIR/src:$PYTHONPATH"

# Couleurs pour l'affichage
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

# Fonction pour vérifier si les dépendances sont installées
check_dependencies() {
    log "Vérification des dépendances..."
    
    # Vérifier Python et venv
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 n'est pas installé"
        exit 1
    fi
    
    # Vérifier Node.js et npm
    if ! command -v node &> /dev/null; then
        log_error "Node.js n'est pas installé"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        log_error "npm n'est pas installé"
        exit 1
    fi
    
    # Vérifier que le virtualenv existe
    if [ ! -d "$BACKEND_DIR/.venv" ]; then
        log_warning "Virtual environment non trouvé, création en cours..."
        python3 -m venv "$BACKEND_DIR/.venv"
    fi
    
    # Activer le virtualenv
    source "$BACKEND_DIR/.venv/bin/activate"
    
    # Installer les dépendances Python si requirements disponibles
    
    # Vérifier les dépendances Node
    if [ ! -f "$FRONTEND_DIR/package.json" ]; then
        log_error "package.json non trouvé dans le frontend"
        exit 1
    fi
    
    log_success "Toutes les dépendances sont présentes"
}

# Fonction pour installer les dépendances si nécessaire
install_dependencies() {
    log "Installation des dépendances si nécessaire..."
    
    # Backend
    source "$BACKEND_DIR/.venv/bin/activate"
    # Installer requirements s'ils existent, sinon packages minimum
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        log "Installation des dépendances backend (local requirements.txt)..."
        pip install -r "$BACKEND_DIR/requirements.txt"
    elif [ -f "$PROJECT_DIR/../requirements.txt" ]; then
        log "Installation des dépendances backend (racine requirements.txt)..."
        pip install -r "$PROJECT_DIR/../requirements.txt"
    elif [ -f "$PROJECT_DIR/../requirements-api-v2.txt" ]; then
        log "Installation des dépendances backend (requirements-api-v2.txt)..."
        pip install -r "$PROJECT_DIR/../requirements-api-v2.txt"
    else
        log_warning "Aucun requirements.txt trouvé, installation minimale (fastapi, uvicorn, pandas)..."
        pip install fastapi uvicorn pandas
    fi
    # Assurer la présence d'uvicorn même si les requirements ne l'incluent pas
    if ! python -c "import uvicorn" 2>/dev/null; then
        log_warning "uvicorn manquant après installation, installation ..."
        pip install uvicorn
    fi
    
    # Frontend
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log "Installation des dépendances frontend..."
        cd "$FRONTEND_DIR"
        npm install
        cd "$PROJECT_DIR"
    fi
    
    log_success "Dépendances installées"
}

# Rafraîchit les séries macro depuis FRED
refresh_macro_series() {
    log "Actualisation des séries macro..."
    if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
        log_warning "Impossible d'actualiser les séries macro (venv absent)"
        return
    fi
    (
        cd "$BACKEND_DIR"
        source "$BACKEND_DIR/.venv/bin/activate"
        python jobs/macro_series_snapshot.py >/tmp/macro_series_snapshot.log 2>&1
    ) && log_success "Séries macro à jour" || log_warning "Actualisation macro a échoué (voir /tmp/macro_series_snapshot.log)"
}

# Rafraîchit les snapshots Market Intelligence avant le démarrage
refresh_market_intel() {
    log "Actualisation des snapshots Market Intelligence..."
    if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
        log_warning "Impossible d'actualiser (venv absent)"
        return
    fi
    (
        cd "$BACKEND_DIR"
        source "$BACKEND_DIR/.venv/bin/activate"
        python jobs/market_intelligence_snapshot.py >/tmp/market_intel_snapshot.log 2>&1
    ) && log_success "Snapshots Market Intelligence à jour" || log_warning "Actualisation Market Intelligence a échoué (voir /tmp/market_intel_snapshot.log)"
}

# Fonction pour démarrer le backend
start_backend() {
    log "Démarrage du backend (API)..."
    
    # Tuer les processus existants
    kill_port 8050
    
    # Démarrer le backend
    cd "$BACKEND_DIR"
    # Propager l'environnement (.env à la racine de copilot-app)
    if [ -f "$ENV_FILE" ]; then
        cp -f "$ENV_FILE" "$BACKEND_DIR/.env"
    fi
    source "$BACKEND_DIR/.venv/bin/activate"
    
    nohup python run_api.py > api.log 2>&1 &
    BACKEND_PID=$!
    
    # Attendre que le backend démarre (wait loop - pas de timeout qui n'existe pas sur macOS)
    log "Attente du démarrage du backend..."
    backend_up=0
    for i in {1..10}; do
        if curl -fsS "http://localhost:8050/api/health" >/dev/null 2>&1; then
            backend_up=1
            break
        fi
        sleep 2
        log "En attente du backend... ($i/10)"
    done
    
    # Vérifier si le backend répond
    if [ $backend_up -eq 1 ]; then
        log_success "Backend démarré avec succès (PID: $BACKEND_PID)"
        echo "$BACKEND_PID" > /tmp/finance_copilot_backend.pid
    else
        log_error "Échec du démarrage du backend"
        tail -20 api.log
        exit 1
    fi
}

# Fonction pour démarrer le frontend
start_frontend() {
    log "Démarrage du frontend..."
    
    # Tuer les processus existants
    kill_port 5173
    
    # Démarrer le frontend
    cd "$FRONTEND_DIR"
    nohup npm run dev > frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Attendre que le frontend démarre (wait loop - pas de timeout qui n'existe pas sur macOS)
    log "Attente du démarrage du frontend..."
    frontend_up=0
    for i in {1..15}; do
        if curl -fsS "http://localhost:5173/" | grep -q "<html" >/dev/null 2>&1; then
            frontend_up=1
            break
        fi
        sleep 2
        log "En attente du frontend... ($i/15)"
    done
    
    # Vérifier si le frontend répond
    if [ $frontend_up -eq 1 ]; then
        log_success "Frontend démarré avec succès (PID: $FRONTEND_PID)"
        echo "$FRONTEND_PID" > /tmp/finance_copilot_frontend.pid
    else
        log_error "Échec du démarrage du frontend"
        tail -20 frontend.log
        exit 1
    fi
    
    cd "$PROJECT_DIR"
}

# Fonction pour arrêter tous les services
stop_services() {
    log "Arrêt des services..."
    
    # Arrêter le backend
    if [ -f /tmp/finance_copilot_backend.pid ]; then
        BACKEND_PID=$(cat /tmp/finance_copilot_backend.pid)
        kill $BACKEND_PID 2>/dev/null || true
        rm -f /tmp/finance_copilot_backend.pid
    fi
    
    # Arrêter le frontend
    if [ -f /tmp/finance_copilot_frontend.pid ]; then
        FRONTEND_PID=$(cat /tmp/finance_copilot_frontend.pid)
        kill $FRONTEND_PID 2>/dev/null || true
        rm -f /tmp/finance_copilot_frontend.pid
    fi
    
    # Tuer les ports
    kill_port 8050
    kill_port 5173
    
    log_success "Tous les services ont été arrêtés"
}

# Fonction pour afficher l'état
status() {
    log "État des services:"
    
    if is_port_in_use 8050; then
        log_success "Backend: EN COURS (port 8050)"
    else
        log_warning "Backend: ARRÊTÉ"
    fi
    
    if is_port_in_use 5173; then
        log_success "Frontend: EN COURS (port 5173)"
    else
        log_warning "Frontend: ARRÊTÉ"
    fi
}

# Fonction pour afficher l'aide
show_help() {
    echo "Finance Copilot - Script de démarrage"
    echo ""
    echo "Usage: $0 [commande]"
    echo ""
    echo "Commandes:"
    echo "  start     Démarre le backend et le frontend"
    echo "  stop      Arrête tous les services"
    echo "  restart   Redémarre tous les services"
    echo "  status    Affiche l'état des services"
    echo "  help      Affiche cette aide"
    echo ""
    echo "URLs:"
    echo "  Frontend: http://localhost:5173"
    echo "  Backend:  http://localhost:8050"
    echo "  Docs API: http://localhost:8050/docs"
}

# Main
main() {
    case "${1:-start}" in
        start)
            check_dependencies
            install_dependencies
            refresh_macro_series
            refresh_market_intel
            start_backend
            start_frontend
            log_success "Finance Copilot est maintenant disponible!"
            echo ""
            echo "🌐 URLs:"
            echo "   Frontend: http://localhost:5173"
            echo "   Backend:  http://localhost:8050"
            echo "   Docs API: http://localhost:8050/docs"
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 3
            check_dependencies
            install_dependencies
            refresh_macro_series
            refresh_market_intel
            start_backend
            start_frontend
            log_success "Services redémarrés avec succès!"
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

# Exécuter la fonction principale
main "$@"
