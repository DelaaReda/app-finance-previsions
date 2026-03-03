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
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/src"
LEGACY_DIR="$BACKEND_DIR/platform/legacy"
# Frontend statique (pas de build npm)
FRONTEND_DIR="$PROJECT_DIR/../web/src/domains/forecasts/pages"
FRONTEND_DIST="$FRONTEND_DIR"
PYTHON_BIN=""

# Résoudre l'interpréteur Python canonique pour ce runtime
resolve_python_bin() {
    if [ -x "$BACKEND_DIR/.venv/bin/python3" ]; then
        echo "$BACKEND_DIR/.venv/bin/python3"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        command -v python
        return 0
    fi
    return 1
}

ensure_python_bin() {
    if [ -n "$PYTHON_BIN" ]; then
        return 0
    fi
    if ! PYTHON_BIN="$(resolve_python_bin)"; then
        log_error "Python introuvable (python3/python)."
        log_error "Exécuter: $PROJECT_DIR/runtime/bootstrap_backend_env.sh"
        exit 1
    fi
}

validate_python_runtime_deps() {
    ensure_python_bin
    local missing
    missing="$("$PYTHON_BIN" - <<'PY'
import importlib.util

required = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pandas": "pandas",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "duckdb": "duckdb",
}

missing = [pkg for mod, pkg in required.items() if importlib.util.find_spec(mod) is None]
print(" ".join(missing))
PY
)"
    if [ -n "$missing" ]; then
        log_error "Dépendances Python manquantes: $missing"
        log_error "Exécuter: $PROJECT_DIR/runtime/bootstrap_backend_env.sh"
        return 1
    fi
    return 0
}

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
    if [ ! -f "$LEGACY_DIR/jobs/validate_and_generate_data.py" ]; then
        log_warning "Job de seed introuvable: $LEGACY_DIR/jobs/validate_and_generate_data.py (skip)"
        return 0
    fi
    ensure_python_bin
    local PY="$PYTHON_BIN"
    # Lancer le job en arrière-plan
    nohup "$PY" "$LEGACY_DIR/jobs/validate_and_generate_data.py" > /tmp/data_generation.log 2>&1 &
    DATA_GEN_PID=$!
    log_success "Job de génération lancé (PID: $DATA_GEN_PID)"
    log "Les données seront disponibles progressivement (voir /tmp/data_generation.log)"
}

# Rafraîchir les snapshots critiques (news, sentiment, macro, quality_gate, judge_enrich)
refresh_live_data() {
    log "Rafraîchissement des données (news, sentiment, macro, quality_gate, judge_enrich)..."
    cd "$BACKEND_DIR"

    ensure_python_bin
    local PY="$PYTHON_BIN"

    export PYTHONPATH="$BACKEND_DIR"

    run_job() {
        local job="$1"
        if [ ! -f "$job" ]; then
            log_warning "Job introuvable: $job (skip)"
            return 0
        fi
        log " → $job"
        if ! "$PY" "$job"; then
            log_warning "Job échoué: $job (on continue, pas de fallback silencieux)"
        fi
    }

    run_job "$LEGACY_DIR/jobs/news_ingest.py"
    run_job "$LEGACY_DIR/jobs/news_sentiment.py"
    run_job "$LEGACY_DIR/jobs/macro_series_snapshot.py"
    if [ -x "$LEGACY_DIR/scripts/fetch_prices_yahoo.sh" ] && [ -n "${YAHOO_COOKIE_FILE:-}" ]; then
        log " → scripts/fetch_prices_yahoo.sh"
        if ! "$LEGACY_DIR/scripts/fetch_prices_yahoo.sh" --cookie "$YAHOO_COOKIE_FILE"; then
            log_warning "Job échoué: scripts/fetch_prices_yahoo.sh (on continue)"
        fi
    fi
    # Stooq fallback is handled directly in jobs/stocks_prices_refresh.py.
    # Keep launcher lean: no separate legacy script dependency here.
    run_job "$LEGACY_DIR/jobs/stocks_prices_refresh.py"

    local quality_gate_ok=true
    log " → jobs/data_quality_gate.py"
    if ! "$PY" "$LEGACY_DIR/jobs/data_quality_gate.py"; then
        quality_gate_ok=false
        log_warning "Job échoué: jobs/data_quality_gate.py (judge_enrich ignoré)"
    else
        if ! "$PY" - <<'PY'
import json
import sys
from pathlib import Path

report_path = Path("data/quality_report.json")
if not report_path.exists():
    print("quality_report_missing")
    sys.exit(2)

try:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
except Exception:
    print("quality_report_invalid")
    sys.exit(2)

audit = payload.get("audit_results") if isinstance(payload, dict) else {}
if not isinstance(audit, dict):
    audit = {}
summary = audit.get("summary")
if not isinstance(summary, dict):
    summary = payload.get("summary") if isinstance(payload, dict) and isinstance(payload.get("summary"), dict) else {}

degraded = audit.get("degraded_flag")
if degraded is None and isinstance(payload, dict):
    degraded = payload.get("degraded_flag")
if degraded is None:
    degraded = int(summary.get("files_failed") or 0) > 0

sys.exit(1 if degraded else 0)
PY
        then
            quality_gate_ok=false
            log_warning "Quality gate en mode degradé: judge_enrich ignoré pour éviter garbage in."
        fi
    fi

    if [ "$quality_gate_ok" = true ]; then
        run_job "$LEGACY_DIR/jobs/judge_enrich.py"
    fi
    run_job "$LEGACY_DIR/jobs/judge_quality_report.py"

    log_success "Rafraîchissement des données terminé."
}

# Tester les modèles G4F (écrit runtime/data/llm/models/tested_g4f_models*.json)
run_g4f_tests() {
    log "Test des modèles G4F..."
    cd "$BACKEND_DIR"

    ensure_python_bin
    local PY="$PYTHON_BIN"

    export PYTHONPATH="$BACKEND_DIR"

    if [ ! -f "$LEGACY_DIR/scripts/test_g4f_models.py" ]; then
        log_warning "⚠️  scripts/test_g4f_models.py introuvable, skip G4F tests."
        return
    fi

    # Ne pas bloquer le démarrage : lancer en arrière-plan
    (
        set +e
        if command -v timeout >/dev/null 2>&1; then
            timeout 120 "$PY" "$LEGACY_DIR/scripts/test_g4f_models.py" > /tmp/g4f_test.log 2>&1
        else
            "$PY" "$LEGACY_DIR/scripts/test_g4f_models.py" > /tmp/g4f_test.log 2>&1
        fi
        rc=$?
        if [ $rc -ne 0 ]; then
            log_warning "⚠️  Tests G4F échoués (rc=$rc). Voir /tmp/g4f_test.log"
        else
            log_success "✅ Tests G4F terminés. Résultats dans runtime/data/llm/models/tested_g4f_models*.json et /tmp/g4f_test.log"
        fi
    ) &
    log "G4F tests lancés en arrière-plan (voir /tmp/g4f_test.log)"
}

# Démarrer le backend
start_backend() {
    log "Démarrage du backend..."

    cd "$BACKEND_DIR"
    # Charger l'environnement (.env backend et racine) pour propager les API keys (OpenRouter, DeepInfra, etc.)
    if [ -f ".env" ]; then
        set -a
        # shellcheck source=/dev/null
        source ".env"
        set +a
    fi
    
    # Export API keys with both naming conventions for compatibility
    if [ -n "$OPEN_ROUTER_API_KEY" ]; then
        export OPEN_ROUTER_API_KEY="$OPEN_ROUTER_API_KEY"
        log "✅ OpenRouter API key loaded"
    fi
    
    # Force use of free g4f models if no auth keys
    if [ -z "$OPEN_ROUTER_API_KEY" ] && [ -z "$DEEPINFRA_API_KEY" ]; then
        log_warning "⚠️ No API keys found, forcing free g4f models"
        export G4F_PROVIDER="Blackbox"  # Free provider
        export ECON_AGENT_MODELS="gpt-4o-mini"  # Free model via g4f
    fi
    
    # Désactiver reload pour éviter segfault sur ARM64
    export FINANCE_COPILOT_RELOAD=0
    # Prefer src/ first so 'api' resolves to src/api (contains services, schemas, etc.)
    export PYTHONPATH="$BACKEND_DIR"
    ensure_python_bin
    local PY="$PYTHON_BIN"
    
    # Démarrer en arrière-plan (logs dans runtime/)
    nohup "$PY" run_api.py > "$SCRIPT_DIR/api.log" 2>&1 &
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
    tail -20 "$SCRIPT_DIR/api.log"
    exit 1
}

# Démarrer le frontend
start_frontend() {
    log "Démarrage du frontend..."

    if [ ! -d "$FRONTEND_DIST" ] || [ ! -f "$FRONTEND_DIST/index.html" ]; then
        log_error "Frontend introuvable dans $FRONTEND_DIST (index.html manquant)"
        exit 1
    fi

    # Servir les fichiers statiques (app/) avec Python (simple et rapide)
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
    
    # Vérification environnement runtime avant tout job
    if ! validate_python_runtime_deps; then
        exit 1
    fi

    # Générer les données en arrière-plan
    generate_initial_data

    # Rafraîchir les données live critiques (synchrones, pas de mock)
    refresh_live_data

    # Tester les modèles G4F (écrit la shortlist pour le runtime)
    run_g4f_tests
    
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
    echo "   Backend  : $SCRIPT_DIR/api.log"
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
