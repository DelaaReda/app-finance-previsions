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

# Ensure backend root + src on PYTHONPATH for standalone jobs
export PYTHONPATH="$BACKEND_DIR:$BACKEND_DIR/src:$PYTHONPATH"

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
    
    # Vérifier que le virtualenv existe et n'est pas corrompu
    VENV_CORRUPTED=false
    if [ ! -d "$BACKEND_DIR/.venv" ]; then
        log_warning "Virtual environment non trouvé, création en cours..."
        VENV_CORRUPTED=true
    elif [ -f "$BACKEND_DIR/.venv/bin/python3" ]; then
        # Tester si le venv fonctionne (pas de liens symboliques en boucle)
        if ! "$BACKEND_DIR/.venv/bin/python3" --version >/dev/null 2>&1; then
            log_warning "Le venv semble corrompu (liens symboliques en boucle), recréation..."
            VENV_CORRUPTED=true
        fi
    else
        log_warning "Le venv existe mais python3 est manquant, recréation..."
        VENV_CORRUPTED=true
    fi
    
    if [ "$VENV_CORRUPTED" = true ]; then
        # Supprimer l'ancien venv s'il existe
        if [ -d "$BACKEND_DIR/.venv" ]; then
            log "Suppression de l'ancien venv corrompu..."
            rm -rf "$BACKEND_DIR/.venv"
        fi
        # Créer un nouveau venv
        log "Création d'un nouveau virtual environment..."
        if ! python3 -m venv "$BACKEND_DIR/.venv" 2>/dev/null; then
            log_error "Échec de la création du venv avec python3 -m venv"
            log_warning "Tentative avec python3 -m virtualenv..."
            if ! python3 -m virtualenv "$BACKEND_DIR/.venv" 2>/dev/null; then
                log_error "Impossible de créer le venv. Installation de python3-venv requise."
                log_error "Sur macOS: brew install python3"
                log_error "Sur Debian/Ubuntu: sudo apt install python3-venv"
                exit 1
            fi
        fi
        log_success "Virtual environment créé"
    fi
    
    # Activer le virtualenv et vérifier qu'il fonctionne
    if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
        source "$BACKEND_DIR/.venv/bin/activate"
        # Vérifier que python fonctionne
        if ! python --version >/dev/null 2>&1; then
            log_error "Le venv activé ne fonctionne pas, recréation..."
            rm -rf "$BACKEND_DIR/.venv"
            python3 -m venv "$BACKEND_DIR/.venv" || python3 -m virtualenv "$BACKEND_DIR/.venv" || {
                log_error "Impossible de recréer le venv"
                exit 1
            }
            source "$BACKEND_DIR/.venv/bin/activate"
        fi
    else
        log_error "Le fichier d'activation du venv n'existe pas: $BACKEND_DIR/.venv/bin/activate"
        log_error "Le venv semble corrompu. Suppression et recréation..."
        rm -rf "$BACKEND_DIR/.venv"
        python3 -m venv "$BACKEND_DIR/.venv" || python3 -m virtualenv "$BACKEND_DIR/.venv" || {
            log_error "Impossible de recréer le venv"
            exit 1
        }
        source "$BACKEND_DIR/.venv/bin/activate"
    fi
    
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
        log "Installation des dépendances backend depuis requirements.txt..."
        # Installer toutes les dépendances depuis requirements.txt
        # Utiliser --upgrade pour s'assurer que les versions sont à jour
        if ! pip install --upgrade -q -r "$BACKEND_DIR/requirements.txt" 2>&1; then
            log_warning "Échec de l'installation complète depuis requirements.txt, installation package par package..."
            # Fallback: installer les packages un par un
            while IFS= read -r line || [ -n "$line" ]; do
                # Ignorer les lignes vides et les commentaires
                [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
                # Extraire le nom du package (avant >=, ==, etc.)
                package=$(echo "$line" | sed 's/[>=<].*//' | xargs)
                if [ -n "$package" ]; then
                    log "Installation de $package..."
                    pip install --upgrade -q "$line" || pip install --upgrade -q "$package" || true
                fi
            done < "$BACKEND_DIR/requirements.txt"
        fi
    elif [ -f "$PROJECT_DIR/../requirements.txt" ]; then
        log "Installation des dépendances backend (racine requirements.txt)..."
        pip install -q -r "$PROJECT_DIR/../requirements.txt"
    elif [ -f "$PROJECT_DIR/../requirements-api-v2.txt" ]; then
        log "Installation des dépendances backend (requirements-api-v2.txt)..."
        pip install -q -r "$PROJECT_DIR/../requirements-api-v2.txt"
    else
        log_warning "Aucun requirements.txt trouvé, installation minimale (fastapi, uvicorn, pandas, requests)..."
        pip install -q fastapi uvicorn pandas requests
    fi
    
    # Vérifier et installer les dépendances critiques manquantes
    for module in "fastapi" "uvicorn" "pandas" "requests"; do
        if ! python -c "import $module" 2>/dev/null; then
            log_warning "$module manquant après installation, installation..."
            # Installer depuis requirements.txt si disponible, sinon version par défaut
            if [ -f "$BACKEND_DIR/requirements.txt" ] && grep -q "^$module" "$BACKEND_DIR/requirements.txt"; then
                pip install --upgrade -q "$(grep "^$module" "$BACKEND_DIR/requirements.txt" | head -1)" || pip install --upgrade -q "$module" || true
            else
                pip install --upgrade -q "$module" || true
            fi
            # Vérifier que l'installation a réussi
            if ! python -c "import $module" 2>/dev/null; then
                log_error "Échec de l'installation de $module"
            else
                log_success "$module installé avec succès"
            fi
        fi
    done
    
    # Installer fredapi si nécessaire (peut ne pas être dans requirements.txt)
    if ! python -c "import fredapi" 2>/dev/null; then
        log "Installation de fredapi (optionnel)..."
        pip install -q fredapi || true
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

# Rafraîchit les séries macro depuis FRED (optionnel, ne bloque pas le démarrage)
refresh_macro_series() {
    log "Actualisation des séries macro..."
    if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
        log_warning "Impossible d'actualiser les séries macro (venv absent)"
        return 0
    fi
    
    # Vérifier si le script existe
    if [ ! -f "$BACKEND_DIR/jobs/macro_series_snapshot.py" ]; then
        log_warning "Script macro_series_snapshot.py non trouvé, skip..."
        return 0
    fi
    
    # Exécuter en arrière-plan pour ne pas bloquer le démarrage
    (
        cd "$BACKEND_DIR"
        source "$BACKEND_DIR/.venv/bin/activate"
        
        # Load .env file if it exists to get FRED_API_KEY
        # Priority: copilot-app/.env (project root)
        if [ -f "$PROJECT_DIR/.env" ]; then
            set -a  # automatically export all variables
            source "$PROJECT_DIR/.env"
            set +a
            log "✅ Loaded .env from $PROJECT_DIR/.env"
        elif [ -f "$BACKEND_DIR/.env" ]; then
            set -a
            source "$BACKEND_DIR/.env"
            set +a
            log "✅ Loaded .env from $BACKEND_DIR/.env"
        fi
        
        # Vérifier que les dépendances nécessaires sont installées
        # install_dependencies() a déjà été appelée, mais on vérifie quand même
        MISSING_DEPS=()
        if ! python -c "import pandas" 2>/dev/null; then
            MISSING_DEPS+=("pandas")
        fi
        if ! python -c "import requests" 2>/dev/null; then
            MISSING_DEPS+=("requests")
        fi
        
        # Si des dépendances manquent, les installer depuis requirements.txt
        if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
            log_warning "Dépendances manquantes détectées: ${MISSING_DEPS[*]}, installation depuis requirements.txt..."
            if [ -f "$BACKEND_DIR/requirements.txt" ]; then
                # Réinstaller depuis requirements.txt pour respecter les versions
                if ! pip install --upgrade -q -r "$BACKEND_DIR/requirements.txt" 2>&1; then
                    # Si échec, installer les packages manquants individuellement
                    for dep in "${MISSING_DEPS[@]}"; do
                        log "Installation de $dep..."
                        if grep -q "^$dep" "$BACKEND_DIR/requirements.txt"; then
                            pip install --upgrade -q "$(grep "^$dep" "$BACKEND_DIR/requirements.txt" | head -1)" || pip install --upgrade -q "$dep" || true
                        else
                            pip install --upgrade -q "$dep" || true
                        fi
                        # Vérifier que l'installation a réussi
                        if python -c "import $dep" 2>/dev/null; then
                            log_success "$dep installé avec succès"
                        else
                            log_error "Échec de l'installation de $dep"
                        fi
                    done
                fi
            else
                # Fallback: installer les packages manquants
                for dep in "${MISSING_DEPS[@]}"; do
                    log "Installation de $dep..."
                    pip install --upgrade -q "$dep" || true
                    if python -c "import $dep" 2>/dev/null; then
                        log_success "$dep installé avec succès"
                    else
                        log_error "Échec de l'installation de $dep"
                    fi
                done
            fi
        fi
        
        # Vérifier fredapi (optionnel, peut ne pas être dans requirements.txt)
        if ! python -c "import fredapi" 2>/dev/null; then
            log "Installation de fredapi (optionnel)..."
            pip install -q fredapi || true
        fi
        
        # Vérifier que pandas est bien installé avant d'exécuter (requis)
        if ! python -c "import pandas" 2>/dev/null; then
            log_warning "pandas n'est toujours pas disponible après installation, skip job macro..."
            return 0
        fi
        
        python jobs/macro_series_snapshot.py >/tmp/macro_series_snapshot.log 2>&1
    ) && log_success "Séries macro à jour" || log_warning "Actualisation macro a échoué (non bloquant, voir /tmp/macro_series_snapshot.log)"
    return 0  # Toujours retourner 0 pour ne pas bloquer le démarrage
}

# Rafraîchit les snapshots Market Intelligence avant le démarrage (optionnel)
refresh_market_intel() {
    log "Actualisation des snapshots Market Intelligence..."
    if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
        log_warning "Impossible d'actualiser (venv absent)"
        return 0
    fi
    
    # Vérifier si le script existe
    if [ ! -f "$BACKEND_DIR/jobs/market_intelligence_snapshot.py" ]; then
        log_warning "Script market_intelligence_snapshot.py non trouvé, skip..."
        return 0
    fi
    
    # Exécuter en arrière-plan pour ne pas bloquer le démarrage
    (
        cd "$BACKEND_DIR"
        source "$BACKEND_DIR/.venv/bin/activate"
        python jobs/market_intelligence_snapshot.py >/tmp/market_intel_snapshot.log 2>&1
    ) && log_success "Snapshots Market Intelligence à jour" || log_warning "Actualisation Market Intelligence a échoué (non bloquant, voir /tmp/market_intel_snapshot.log)"
    return 0  # Toujours retourner 0 pour ne pas bloquer le démarrage
}

# Valide et génère toutes les données nécessaires (non bloquant)
validate_and_generate_data() {
    log "Validation et génération des données nécessaires..."
    if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
        log_warning "Impossible de valider les données (venv absent)"
        return 0
    fi
    
    # Vérifier si le script existe
    if [ ! -f "$BACKEND_DIR/jobs/validate_and_generate_data.py" ]; then
        log_warning "Script validate_and_generate_data.py non trouvé, skip..."
        return 0
    fi
    
    # Exécuter en arrière-plan pour ne pas bloquer le démarrage
    (
        cd "$BACKEND_DIR"
        source "$BACKEND_DIR/.venv/bin/activate"
        
        # Load .env file if it exists
        if [ -f "$PROJECT_DIR/.env" ]; then
            set -a
            source "$PROJECT_DIR/.env"
            set +a
        elif [ -f "$BACKEND_DIR/.env" ]; then
            set -a
            source "$BACKEND_DIR/.env"
            set +a
        fi
        
        python jobs/validate_and_generate_data.py >/tmp/validate_data.log 2>&1
    ) && log_success "Données validées et générées" || log_warning "Validation des données a échoué (non bloquant, voir /tmp/validate_data.log)"
    return 0  # Toujours retourner 0 pour ne pas bloquer le démarrage
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
    
    # Vérifier et activer le venv
    if [ ! -f "$BACKEND_DIR/.venv/bin/activate" ]; then
        log_error "Le venv n'existe pas ou est corrompu. Création en cours..."
        rm -rf "$BACKEND_DIR/.venv"
        if ! python3 -m venv "$BACKEND_DIR/.venv" 2>/dev/null; then
            if ! python3 -m virtualenv "$BACKEND_DIR/.venv" 2>/dev/null; then
                log_error "Impossible de créer le venv"
                exit 1
            fi
        fi
        log_success "Venv recréé"
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
            # Vérifier que les dépendances critiques sont bien installées avant les jobs
            source "$BACKEND_DIR/.venv/bin/activate"
            if ! python -c "import pandas" 2>/dev/null; then
                log_warning "pandas manquant après install_dependencies, réinstallation..."
                if [ -f "$BACKEND_DIR/requirements.txt" ]; then
                    pip install --upgrade -q "$(grep '^pandas' "$BACKEND_DIR/requirements.txt" | head -1)" || pip install --upgrade -q pandas || true
                else
                    pip install --upgrade -q pandas || true
                fi
                # Vérifier à nouveau
                if ! python -c "import pandas" 2>/dev/null; then
                    log_error "pandas n'a pas pu être installé, le job macro échouera"
                else
                    log_success "pandas installé avec succès"
                fi
            fi
            # Jobs optionnels - ne bloquent pas le démarrage
            refresh_macro_series || true
            refresh_market_intel || true
            # Valider et générer toutes les données nécessaires (non bloquant)
            validate_and_generate_data || true
            start_backend
            start_frontend
            log_success "Finance Copilot est maintenant disponible!"
            echo ""
            echo "🌐 URLs:"
            echo "   Frontend: http://localhost:5173"
            echo "   Backend:  http://localhost:8050"
            echo "   Docs API: http://localhost:8050/docs"
            echo ""
            echo "ℹ️  Note: Les jobs de génération de données s'exécutent automatiquement au démarrage"
            echo "   si les données sont manquantes (voir logs backend pour détails)"
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
