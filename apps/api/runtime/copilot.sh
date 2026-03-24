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
WORKSPACE_ROOT="$(cd "$PROJECT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/src"
LEGACY_DIR="$BACKEND_DIR/platform/legacy"
# Frontend statique (pas de build npm)
FRONTEND_DIR="$PROJECT_DIR/../web/src/domains/forecasts/pages"
FRONTEND_DIST="$FRONTEND_DIR"
MONITOR_GUARD_SCRIPT="$WORKSPACE_ROOT/scripts/monitor_stack_guard.sh"
MONITOR_SERVER_SCRIPT="$WORKSPACE_ROOT/apps/monitor/server.py"
MONITOR_URL="${FC_MONITOR_LOCAL_URL:-http://localhost:7779}"
BACKEND_START_TIMEOUT_SECONDS="${FC_BACKEND_START_TIMEOUT_SECONDS:-120}"
MONITOR_START_TIMEOUT_SECONDS="${FC_MONITOR_START_TIMEOUT_SECONDS:-45}"
RUNTIME_STACK_SETTLE_SECONDS="${FC_RUNTIME_STACK_SETTLE_SECONDS:-20}"
MONITOR_REQUIRED="${FC_MONITOR_REQUIRED:-1}"
SYSTEMD_BACKEND_UNIT="finance-backend.service"
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
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -i ":$port" >/dev/null 2>&1
        return $?
    fi
    if command -v ss >/dev/null 2>&1; then
        ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[\\.:]${port}\$"
        return $?
    fi
    return 1
}

is_pid_alive() {
    local pid_file="$1"
    local pid=""
    if [ ! -f "$pid_file" ]; then
        return 1
    fi
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
        return 1
    fi
    kill -0 "$pid" >/dev/null 2>&1
}

listener_pid_for_port() {
    local port="$1"
    local pid=""
    if command -v lsof >/dev/null 2>&1; then
        pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
        if [[ "$pid" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$pid"
            return 0
        fi
    fi
    if command -v ss >/dev/null 2>&1; then
        pid="$(ss -ltnp "( sport = :$port )" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -n 1 || true)"
        if [[ "$pid" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$pid"
            return 0
        fi
    fi
    return 1
}

persist_listener_pid() {
    local port="$1"
    local pid_file="$2"
    local fallback_pid="${3:-}"
    local pid=""
    pid="$(listener_pid_for_port "$port" || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo "$pid" > "$pid_file"
        return 0
    fi
    if [[ "$fallback_pid" =~ ^[0-9]+$ ]]; then
        echo "$fallback_pid" > "$pid_file"
        return 0
    fi
    return 1
}

backend_ready() {
    curl -fsS "http://localhost:8050/api/health" >/dev/null 2>&1
}

frontend_ready() {
    curl -fsS "http://localhost:5173/" >/dev/null 2>&1
}

monitor_access_ready() {
    curl -fsS -m 5 "http://localhost:7779/api/monitor/access" >/dev/null 2>&1
}

monitor_contract_ready() {
    monitor_access_ready \
        && curl -fsS -m 5 "http://localhost:7779/api/status?lite=1" >/dev/null 2>&1
}

monitor_ready() {
    local attempts="${1:-3}"
    local tried=0
    while [ "$tried" -lt "$attempts" ]; do
        if monitor_access_ready; then
            return 0
        fi
        sleep 1
        tried=$((tried + 1))
    done
    return 1
}

runtime_stack_ready() {
    backend_ready && frontend_ready && monitor_contract_ready
}

wait_runtime_stack_ready() {
    local timeout="${1:-20}"
    local waited=0
    while [ "$waited" -lt "$timeout" ]; do
        if runtime_stack_ready; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

service_running() {
    local kind="$1"
    local pid_file="$2"
    local port="$3"
    case "$kind" in
        backend)
            backend_ready && return 0
            ;;
        frontend)
            frontend_ready && return 0
            ;;
        monitor)
            # Monitor status should reflect live API reachability, without requiring
            # the heavier status contract on every `status` call.
            monitor_ready 2 && return 0
            return 1
            ;;
    esac
    is_port_in_use "$port" && return 0
    is_pid_alive "$pid_file" && return 0
    return 1
}

has_systemd_backend_unit() {
    systemctl --user list-unit-files "$SYSTEMD_BACKEND_UNIT" --no-legend >/dev/null 2>&1
}

# Arrêter proprement les services
stop_services() {
    log "Arrêt des services existants..."
    
    # Arrêter backend
    if has_systemd_backend_unit; then
        systemctl --user stop "$SYSTEMD_BACKEND_UNIT" >/dev/null 2>&1 || true
    fi
    pkill -f "python.*run_api.py" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    
    # Arrêter frontend
    pkill -f "http.server 5173" 2>/dev/null || true
    pkill -f "vite.*5173" 2>/dev/null || true

    # Arrêter monitor (serveur API/dashboard)
    pkill -f "apps/monitor/server.py|uvicorn.*7779" 2>/dev/null || true
    
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

    local quality_gate_allows_judge_enrich=true
    local quality_gate_mode="unknown"
    local quality_gate_domains="none"
    log " → jobs/data_quality_gate.py"
    if ! "$PY" "$LEGACY_DIR/jobs/data_quality_gate.py"; then
        quality_gate_allows_judge_enrich=false
        log_warning "Job échoué: jobs/data_quality_gate.py (judge_enrich ignoré)"
    else
        local quality_gate_eval=""
        set +e
        quality_gate_eval="$("$PY" - <<'PY'
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

degraded_domains = summary.get("degraded_domains") or []
if not isinstance(degraded_domains, list):
    degraded_domains = []
degraded_domains = [str(x).strip().lower() for x in degraded_domains if str(x).strip()]
domains_csv = ",".join(degraded_domains) if degraded_domains else "none"

if degraded and set(degraded_domains) == {"judge"}:
    print(f"QUALITY_GATE_MODE=soft_degraded_judge_only")
    print(f"QUALITY_GATE_DEGRADED_DOMAINS={domains_csv}")
    sys.exit(0)

if degraded:
    print("QUALITY_GATE_MODE=hard_degraded")
    print(f"QUALITY_GATE_DEGRADED_DOMAINS={domains_csv}")
    sys.exit(1)

print("QUALITY_GATE_MODE=ok")
print(f"QUALITY_GATE_DEGRADED_DOMAINS={domains_csv}")
sys.exit(0)
PY
)"
        local quality_gate_rc=$?
        set -e
        quality_gate_mode="$(printf '%s\n' "$quality_gate_eval" | sed -n 's/^QUALITY_GATE_MODE=//p' | tail -n1)"
        quality_gate_domains="$(printf '%s\n' "$quality_gate_eval" | sed -n 's/^QUALITY_GATE_DEGRADED_DOMAINS=//p' | tail -n1)"
        quality_gate_mode="${quality_gate_mode:-unknown}"
        quality_gate_domains="${quality_gate_domains:-none}"

        if [ "$quality_gate_rc" -ne 0 ]; then
            quality_gate_allows_judge_enrich=false
        fi

        if [ "$quality_gate_mode" = "soft_degraded_judge_only" ]; then
            log_warning "Quality gate soft-degraded (judge-only): judge_enrich autorisé (domains=${quality_gate_domains})"
        elif [ "$quality_gate_mode" = "hard_degraded" ]; then
            log_warning "Quality gate en mode degradé: judge_enrich ignoré pour éviter garbage in. (domains=${quality_gate_domains})"
        else
            log "Quality gate status: ${quality_gate_mode} (domains=${quality_gate_domains})"
        fi
    fi

    if [ "$quality_gate_allows_judge_enrich" = true ]; then
        run_job "$LEGACY_DIR/jobs/judge_enrich.py"
    else
        log_warning "judge_enrich skip (quality_gate_mode=${quality_gate_mode}, degraded_domains=${quality_gate_domains})"
    fi
    log " → jobs/judge_quality_report.py"
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

launch_post_start_refresh() {
    log "Lancement du rafraîchissement live en arrière-plan..."
    (
        set +e
        refresh_live_data
    ) > /tmp/finance_copilot_refresh.log 2>&1 &
    REFRESH_PID=$!
    echo "$REFRESH_PID" > /tmp/finance_copilot_refresh.pid
    log "Refresh live en arrière-plan (PID: $REFRESH_PID, log: /tmp/finance_copilot_refresh.log)"
}

# Démarrer le backend
start_backend() {
    log "Démarrage du backend..."
    local backend_timeout="$BACKEND_START_TIMEOUT_SECONDS"
    if ! [[ "$backend_timeout" =~ ^[0-9]+$ ]] || [ "$backend_timeout" -lt 15 ]; then
        backend_timeout=90
    fi

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

    if has_systemd_backend_unit; then
        log "Backend systemd détecté: $SYSTEMD_BACKEND_UNIT (restart de l'unité)"
        if ! systemctl --user restart "$SYSTEMD_BACKEND_UNIT"; then
            log_error "Échec restart $SYSTEMD_BACKEND_UNIT"
            systemctl --user status "$SYSTEMD_BACKEND_UNIT" --no-pager --lines=40 || true
            exit 1
        fi
        BACKEND_PID="$(systemctl --user show -p MainPID --value "$SYSTEMD_BACKEND_UNIT" 2>/dev/null || echo "")"
        if [ -n "$BACKEND_PID" ]; then
            echo "$BACKEND_PID" > /tmp/finance_copilot_backend.pid
        fi
    else
        # Démarrer en arrière-plan (logs dans runtime/)
        nohup "$PY" run_api.py > "$SCRIPT_DIR/api.log" 2>&1 &
        BACKEND_PID=$!
        echo "$BACKEND_PID" > /tmp/finance_copilot_backend.pid
    fi
    
    # Attendre que le backend réponde
    log "Attente du démarrage du backend (timeout=${backend_timeout}s)..."
    local waited=0
    while [ "$waited" -lt "$backend_timeout" ]; do
        if curl -fsS "http://localhost:8050/api/health" >/dev/null 2>&1; then
            log_success "✅ Backend opérationnel (PID: $BACKEND_PID)"
            log_success "   URL: http://localhost:8050"
            log_success "   Docs: http://localhost:8050/docs"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    log_error "Le backend n'a pas démarré dans ${backend_timeout}s"
    if has_systemd_backend_unit; then
        journalctl --user -u "$SYSTEMD_BACKEND_UNIT" -n 40 --no-pager || true
    else
        tail -20 "$SCRIPT_DIR/api.log"
    fi
    exit 1
}

# Démarrer le frontend
start_frontend() {
    log "Démarrage du frontend..."

    if [ ! -d "$FRONTEND_DIST" ] || [ ! -f "$FRONTEND_DIST/index.html" ]; then
        log_error "Frontend introuvable dans $FRONTEND_DIST (index.html manquant)"
        exit 1
    fi

    # Servir les fichiers statiques (app/) avec Python (simple et rapide).
    # `setsid` keeps the static server alive after the launcher exits; some VM
    # sessions were leaving a stale PID while the frontend listener disappeared.
    cd "$FRONTEND_DIST"
    if command -v setsid >/dev/null 2>&1; then
        setsid python3 -m http.server 5173 </dev/null > /tmp/frontend.log 2>&1 &
    else
        nohup python3 -m http.server 5173 </dev/null > /tmp/frontend.log 2>&1 &
    fi
    FRONTEND_PID=$!
    
    # Attendre que le frontend réponde
    log "Attente du démarrage du frontend..."
    for i in {1..10}; do
        if curl -fsS "http://localhost:5173/" >/dev/null 2>&1; then
            persist_listener_pid 5173 /tmp/finance_copilot_frontend.pid "$FRONTEND_PID" || true
            if is_pid_alive /tmp/finance_copilot_frontend.pid; then
                FRONTEND_PID="$(cat /tmp/finance_copilot_frontend.pid 2>/dev/null || echo "$FRONTEND_PID")"
            fi
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

# Démarrer le monitor runtime (dashboard orchestration)
wait_monitor_ready() {
    local timeout="${1:-25}"
    local waited=0
    while [ "$waited" -lt "$timeout" ]; do
        if monitor_contract_ready; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

start_monitor() {
    log "Démarrage du monitor..."
    local monitor_timeout="$MONITOR_START_TIMEOUT_SECONDS"
    if ! [[ "$monitor_timeout" =~ ^[0-9]+$ ]] || [ "$monitor_timeout" -lt 5 ]; then
        monitor_timeout=25
    fi

    if [ -x "$MONITOR_GUARD_SCRIPT" ]; then
        if ! bash "$MONITOR_GUARD_SCRIPT"; then
            log_warning "monitor_stack_guard.sh a retourné non-zero; vérification des endpoints monitor avant fallback direct"
        fi
        if wait_monitor_ready "$monitor_timeout"; then
            log_success "✅ Monitor opérationnel"
            log_success "   URL: $MONITOR_URL"
            return 0
        fi
        log_warning "Monitor guard exécuté mais endpoints monitor indisponibles"
    fi

    if [ -f "$MONITOR_SERVER_SCRIPT" ]; then
        local monitor_python="$WORKSPACE_ROOT/apps/monitor/.venv/bin/python"
        if [ ! -x "$monitor_python" ]; then
            monitor_python="python3"
        fi
        if is_port_in_use 7779 && ! monitor_ready; then
            log_warning "Port 7779 occupé sans endpoints monitor valides, nettoyage du process stale..."
            pkill -f "apps/monitor/server.py|uvicorn.*7779" 2>/dev/null || true
            sleep 1
        fi
        mkdir -p "$WORKSPACE_ROOT/logs-codex-runs"
        nohup env FC_MONITOR_ROOT="$WORKSPACE_ROOT" "$monitor_python" "$MONITOR_SERVER_SCRIPT" >> "$WORKSPACE_ROOT/logs-codex-runs/monitor-server.log" 2>&1 &
        MONITOR_PID=$!
        echo "$MONITOR_PID" > /tmp/finance_copilot_monitor.pid
        if wait_monitor_ready "$monitor_timeout"; then
            log_success "✅ Monitor opérationnel (direct)"
            log_success "   URL: $MONITOR_URL"
            return 0
        fi
    fi

    if [[ "$MONITOR_REQUIRED" == "1" ]]; then
        log_error "Monitor non démarré (URL attendue: $MONITOR_URL)"
        return 1
    fi
    log_warning "Monitor non démarré (URL attendue: $MONITOR_URL)"
    return 0
}

# Afficher le statut
status() {
    echo ""
    echo "📊 État des services Finance Copilot"
    echo "======================================"
    
    if service_running backend /tmp/finance_copilot_backend.pid 8050; then
        echo -e "${GREEN}✅ Backend${NC}  : EN COURS (http://localhost:8050)"
    else
        echo -e "${RED}❌ Backend${NC}  : ARRÊTÉ"
    fi
    
    if service_running frontend /tmp/finance_copilot_frontend.pid 5173; then
        echo -e "${GREEN}✅ Frontend${NC} : EN COURS (http://localhost:5173)"
    else
        echo -e "${RED}❌ Frontend${NC} : ARRÊTÉ"
    fi

    if service_running monitor /tmp/finance_copilot_monitor.pid 7779; then
        echo -e "${GREEN}✅ Monitor${NC}  : EN COURS (${MONITOR_URL})"
    else
        echo -e "${RED}❌ Monitor${NC}  : ARRÊTÉ"
    fi
    
    echo ""
}

brief() {
    ensure_python_bin

    local output
    if ! output="$(FC_COPILOT_SOURCE_ONLY=1 PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" - <<'PY'
from domains.copilot.application import copilot_service

brief = copilot_service._load_daily_brief_payload()

summary = str(brief.get("summary") or "No daily brief available yet.").strip()
sentiment = str(brief.get("market_sentiment") or brief.get("sentiment") or "UNKNOWN").strip() or "UNKNOWN"
freshness = str(brief.get("freshness") or brief.get("generated_at") or "").strip()

print("BRIEF DU JOUR")
print(f"Sentiment: {sentiment}")
if freshness:
    print(f"Freshness: {freshness}")
print("")
print(summary)

macro = brief.get("macro_signals") if isinstance(brief.get("macro_signals"), list) else []
if macro:
    labels = [copilot_service._brief_signal_label(item, "macro") for item in macro[:4]]
    labels = [item for item in labels if item]
    if labels:
        print("")
        print("Macro: " + " | ".join(labels))

sector_rotation = brief.get("sector_rotation") if isinstance(brief.get("sector_rotation"), dict) else {}
top = copilot_service._brief_list_values(sector_rotation.get("top"))[:3]
bottom = copilot_service._brief_list_values(sector_rotation.get("bottom"))[:3]
if top or bottom:
    print("")
    if top:
        print("Secteurs forts: " + ", ".join(top))
    if bottom:
        print("Secteurs faibles: " + ", ".join(bottom))

top_signals = copilot_service._brief_list_values(brief.get("top_signals"))[:3]
if top_signals:
    print("")
    print("Signaux: " + " | ".join(top_signals))

top_risks = copilot_service._brief_list_values(brief.get("top_risks"))[:3]
if top_risks:
    print("")
    print("Risques: " + " | ".join(top_risks))
PY
)"; then
        log_error "Impossible de générer le brief du jour."
        return 1
    fi

    printf '%s\n' "$output"
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
    
    # Démarrer les services
    start_backend
    start_frontend
    start_monitor

    local settle_timeout="$RUNTIME_STACK_SETTLE_SECONDS"
    if ! [[ "$settle_timeout" =~ ^[0-9]+$ ]] || [ "$settle_timeout" -lt 5 ]; then
        settle_timeout=20
    fi
    log "Vérification finale de la stabilité runtime (timeout=${settle_timeout}s)..."
    if ! wait_runtime_stack_ready "$settle_timeout"; then
        log_error "La stack runtime n'est pas stable après démarrage"
        return 1
    fi

    # Les jobs lourds restent hors chemin critique pour rendre la stack
    # disponible rapidement après un restart runtime.
    launch_post_start_refresh

    # Tester les modèles G4F (écrit la shortlist pour le runtime)
    run_g4f_tests
    
    echo ""
    log_success "🎉 Finance Copilot est opérationnel!"
    echo ""
    echo "🌐 URLs disponibles:"
    echo "   Frontend : http://localhost:5173"
    echo "   Backend  : http://localhost:8050"
    echo "   Docs API : http://localhost:8050/docs"
    echo "   Monitor  : $MONITOR_URL"
    echo ""
    echo "📝 Logs:"
    echo "   Backend  : $SCRIPT_DIR/api.log"
    echo "   Frontend : /tmp/frontend.log"
    echo "   Monitor  : $WORKSPACE_ROOT/logs-codex-runs/monitor-server.log"
    echo ""
}

# Afficher l'aide
show_help() {
    cat << EOF
Finance Copilot - Script optimisé (ARM64/VM)

Usage: $0 [commande]

Commandes:
  brief    Affiche le brief du jour en CLI
  start    Démarre (ou redémarre) les services
  stop     Arrête tous les services
  restart  Redémarre tous les services
  status   Affiche l'état des services
  help     Affiche cette aide

URLs:
  Frontend : http://localhost:5173
  Backend  : http://localhost:8050
  Docs API : http://localhost:8050/docs
  Monitor  : $MONITOR_URL

Note: Ce script optimisé utilise le build frontend existant
et désactive le reload du backend pour éviter les problèmes
sur architecture ARM64.
EOF
}

# Main
main() {
    case "${1:-help}" in
        brief)
            brief
            ;;
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

if [[ "${FC_COPILOT_SOURCE_ONLY:-0}" != "1" ]]; then
    main "$@"
fi
