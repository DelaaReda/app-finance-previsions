# Makefile for Finance Copilot Project

.PHONY: help install run-api-v2 test-api-v2 run-webapp health docs clean

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
