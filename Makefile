# Makefile for Finance Copilot Project

.PHONY: help install run-api-v2 test-api-v2 run-webapp health docs clean
.PHONY: agent-help agent-venv agent-deps agent-check agent-smoke agent-run agent-doc agent-doc-direct
.PHONY: agent-index

# Default target
help:
	@echo "Finance Copilot - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install         Install all dependencies"
	@echo "  make install-api     Install API v2 dependencies only"
	@echo ""
	@echo "Development:"
	@echo "  make run-api-v2      Start FastAPI backend v0.1 (port 8050)"
	@echo "  make run-webapp      Start React frontend (port 5173)"
	@echo "  make fullstack       Start both backend and frontend"
	@echo ""
	@echo "Testing:"
	@echo "  make test-api-v2     Run API smoke tests"
	@echo "  make health          Quick health check"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs            Open API documentation in browser"
	@echo "  make openapi         View OpenAPI spec"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           Remove cache and temp files"
	@echo ""
	@echo "Agent (agent-stack-oss):"
	@echo "  make agent-help      Show agent-related commands"
	@echo "  make agent-venv      Create venv for agent-stack-oss"
	@echo "  make agent-deps      Install agent dependencies"
	@echo "  make agent-check     Run ruff + mypy + pytest for agent"
	@echo "  make agent-smoke     Run pytest smoke for agent"
	@echo "  make agent-run GOAL=\"...\" [HF_EMBED_MODEL=...]  Run agent with G4F + strong embeddings"
	@echo "  make agent-doc       Generate architecture/integration plan (doc-first)"
	@echo "  make agent-doc-direct  Generate docs via direct file write (no git)"
	@echo "  make agent-index     Build/refresh agent RAG index (agent docs + repo docs)"

AGENT_DIR := agent-stack-oss
AGENT_VENV := $(AGENT_DIR)/.venv
ACTIVATE := . $(AGENT_VENV)/bin/activate

agent-help:
	@echo "Agent commands (in $(AGENT_DIR))"
	@echo "  make agent-venv      # Create Python venv"
	@echo "  make agent-deps      # Install requirements"
	@echo "  make agent-check     # ruff + mypy + pytest"
	@echo "  make agent-smoke     # pytest"
	@echo "  make agent-run GOAL=\"...\" [HF_EMBED_MODEL=...]"
	@echo "  make agent-doc       # Doc-first run to draft integration plan"

agent-venv:
	python3 -m venv $(AGENT_VENV)

agent-deps: agent-venv
	$(ACTIVATE) && python -m pip install --upgrade pip && pip install -r $(AGENT_DIR)/requirements.txt

agent-check:
	$(ACTIVATE) && cd $(AGENT_DIR) && ruff check --fix && mypy src && PYTHONPATH=. pytest -q

agent-smoke:
	$(ACTIVATE) && cd $(AGENT_DIR) && PYTHONPATH=. pytest -q

# Usage: make agent-run GOAL="Refactor module X" [HF_EMBED_MODEL=BAAI/bge-large-en-v1.5]
agent-run:
	@[ -n "$(GOAL)" ] || (echo "ERROR: provide GOAL=\"...\"" && exit 1)
	$(ACTIVATE) && cd $(AGENT_DIR) \
	&& export LLM_PROVIDER=g4f \
	&& export HF_EMBED_MODEL=$${HF_EMBED_MODEL:-intfloat/multilingual-e5-large-instruct} \
	&& export G4F_TEMPERATURE=$${G4F_TEMPERATURE:-0.2} \
	&& export G4F_MAX_TOKENS=$${G4F_MAX_TOKENS:-2048} \
	&& export G4F_TIMEOUT=$${G4F_TIMEOUT:-60} \
	&& export G4F_RETRIES=$${G4F_RETRIES:-1} \
	&& export G4F_MODELS=$${G4F_MODELS:-deepseek-ai/DeepSeek-R1-0528,deepseek-ai/DeepSeek-V3-0324-Turbo,deepseek-ai/DeepSeek-V3,Qwen/Qwen3-235B-A22B-Thinking-2507,Qwen/Qwen3-235B-A22B-Instruct-2507,Qwen/Qwen3-Next-80B-A3B-Instruct,zai-org/GLM-4.5,meta-llama/Llama-3.3-70B-Instruct-Turbo,openai/gpt-oss-120b} \
	&& mkdir -p docs && [ -f docs/README.md ] || echo "Agent OSS doc placeholder" > docs/README.md \
	&& PYTHONPATH=. python -m src.agent.run --verbose --goal "$(GOAL)"

agent-doc:
	$(MAKE) agent-run GOAL="Rédige docs/dev/ARCHITECTURE_INTEGRATION_PLAN.md: features, interfaces, dataflows, ADR, plan incrémental; aucune modification code."

# Same as agent-doc but forces direct file write mode (bypass git apply/commit).
agent-doc-direct:
	ALLOW_DIRECT_WRITE=1 $(MAKE) agent-run GOAL="Rédige docs/dev/ARCHITECTURE_INTEGRATION_PLAN.md: features, interfaces, dataflows, ADR, plan incrémental; aucune modification code."

# Build/refresh the vector index for both agent docs and repo root docs
agent-index:
	$(ACTIVATE) && cd $(AGENT_DIR) \
	&& AGENT_DEBUG=1 PYTHONPATH=. python -c "from pathlib import Path; from src.agent.tools.rag_tools import build_or_load_index as b; print('[index] agent docs -> docs'); b('docs'); root=str((Path.cwd()/'..'/'docs').resolve()); print(f'[index] root docs -> {root}'); b(root); print('[index] done')"

# Installation
install:
	pip install -r requirements.txt
	pip install -r requirements-api-v2.txt
	cd webapp && npm install

install-api:
	pip install -r requirements-api-v2.txt

# API v2
run-api-v2:
	@echo "🚀 Starting FastAPI backend v0.1 on port 8050..."
	python scripts/run_api_v2.py --port 8050

# Frontend
run-webapp:
	@echo "🚀 Starting React frontend on port 5173..."
	cd webapp && npm run dev

# Full stack
fullstack:
	@echo "🚀 Starting full stack (backend + frontend)..."
	@echo ""
	@echo "Backend will run on: http://localhost:8050"
	@echo "Frontend will run on: http://localhost:5173"
	@echo ""
	@echo "Press Ctrl+C to stop both servers"
	@echo ""
	@$(MAKE) run-api-v2 & $(MAKE) run-webapp

# Testing
test-api-v2:
	@echo "🧪 Running API v0.1 smoke tests..."
	python scripts/test_api_v2.py

health:
	@echo "🏥 Checking API health..."
	@curl -s http://localhost:8050/api/health | python -m json.tool || echo "❌ API not running on port 8050"

# Documentation
docs:
	@echo "📚 Opening API documentation..."
	@open http://localhost:8050/api/docs || xdg-open http://localhost:8050/api/docs || echo "Please open http://localhost:8050/api/docs manually"

openapi:
	@echo "📄 OpenAPI specification:"
	@curl -s http://localhost:8050/api/openapi.json | python -m json.tool

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true
	rm -rf dist 2>/dev/null || true
	rm -rf build 2>/dev/null || true
	@echo "✨ Cleanup complete!"

# Quick start for new developers
quickstart:
	@echo "🎯 Quick Start Guide"
	@echo "==================="
	@echo ""
	@echo "1. Install dependencies:"
	@echo "   make install"
	@echo ""
	@echo "2. Start backend:"
	@echo "   make run-api-v2"
	@echo ""
	@echo "3. In another terminal, start frontend:"
	@echo "   make run-webapp"
	@echo ""
	@echo "4. Open in browser:"
	@echo "   Frontend: http://localhost:5173"
	@echo "   API Docs: http://localhost:8050/api/docs"
	@echo ""
	@echo "5. Run tests:"
	@echo "   make test-api-v2"
	@echo ""
