#!/usr/bin/env bash
#
# Bootstrap runtime Python environment for Finance Copilot backend.
# VM-first script: creates/updates apps/api/src/.venv and installs runtime deps.
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $1"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')]${NC} $1"; }

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
RUNTIME_DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_DIR="$(cd "$RUNTIME_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/src"
VENV_DIR="$BACKEND_DIR/.venv"
REQ_FILE="$BACKEND_DIR/requirements.runtime.txt"

if ! command -v python3 >/dev/null 2>&1; then
    log_error "python3 introuvable."
    exit 1
fi

if [ ! -f "$REQ_FILE" ]; then
    log_error "Manifest introuvable: $REQ_FILE"
    exit 1
fi

log "Bootstrap env backend runtime..."
log "Backend dir: $BACKEND_DIR"
log "Venv dir: $VENV_DIR"
log "Requirements: $REQ_FILE"

if [ -L "$VENV_DIR" ] && [ ! -x "$VENV_DIR/bin/python3" ]; then
    log_warning "Virtualenv symlink incomplet détecté, réinitialisation..."
    rm -f "$VENV_DIR"
fi

if [ -d "$VENV_DIR" ] && [ ! -x "$VENV_DIR/bin/python3" ]; then
    log_warning "Virtualenv incomplet détecté, réinitialisation..."
    rm -rf "$VENV_DIR"
fi

if [ ! -x "$VENV_DIR/bin/python3" ]; then
    log "Création du virtualenv..."
    python3 -m venv "$VENV_DIR"
else
    log "Virtualenv existant détecté."
fi

PY="$VENV_DIR/bin/python3"

log "Mise à jour pip/setuptools/wheel..."
"$PY" -m pip install --upgrade pip setuptools wheel

log "Installation des dépendances runtime..."
"$PY" -m pip install -r "$REQ_FILE"

log "Validation des modules critiques..."
"$PY" - <<'PY'
import importlib.util
import sys

required = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pandas": "pandas",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "duckdb": "duckdb",
}

missing = [pkg for mod, pkg in required.items() if importlib.util.find_spec(mod) is None]
if missing:
    print("missing:", ", ".join(missing))
    sys.exit(1)
print("ok")
PY

log_success "Environment backend prêt."
log_success "Commande de démarrage: ./finance-copilot.sh start"
