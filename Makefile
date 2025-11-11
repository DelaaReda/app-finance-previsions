# Makefile for Financial Analysis System

.PHONY: ingest-demo
ingest-demo:
	bash services/ingestion/run_ingestion.sh

.PHONY: install-ingestion
install-ingestion:
	python3 -m venv venv
	./venv/bin/pip install --break-system-packages -r services/ingestion/requirements.txt

.PHONY: install
install:
	python3 -m venv venv
	./venv/bin/pip install --break-system-packages -r requirements.txt
	./venv/bin/pip install --break-system-packages -r services/ingestion/requirements.txt

.PHONY: test-ingestion
test-ingestion:
	python3 -c "import sys; sys.path.append('services/ingestion'); from ingestion_service import IngestionService; print('Ingestion service imported successfully')"