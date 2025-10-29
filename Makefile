# Prefer python3, fallback to python
PYTHON := $(shell command -v python3 || command -v python)

.PHONY: test smoke it-integration

test:
	$(PYTHON) -m pytest -q

smoke:
	PYTHONPATH=$$PWD $(PYTHON) scripts/smoke_run.py

it-integration:
	AF_ALLOW_INTERNET=1 PYTHONPATH=$$PWD/src $(PYTHON) -m pytest -m integration -q

# --- Convenience targets that auto-activate the venv ---
.PHONY: venv-install test-venv it-integration-venv

venv-install:
	. .venv/bin/activate && python -m pip install -r requirements.txt

test-venv:
	. .venv/bin/activate && PYTHONPATH=$$PWD/src python -m pytest -q

it-integration-venv:
	. .venv/bin/activate && AF_ALLOW_INTERNET=1 PYTHONPATH=$$PWD/src python -m pytest -m integration -q

# --- LLM model watcher and agents ---
.PHONY: g4f-refresh llm-agents harvester-once

G4F_LIMIT ?= 8

g4f-refresh:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.g4f_model_watcher --refresh --limit $(G4F_LIMIT)

.PHONY: g4f-refresh-official
g4f-refresh-official:
	G4F_SOURCE=official PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.g4f_model_watcher --refresh --limit $(G4F_LIMIT)

.PHONY: g4f-fetch-official
g4f-fetch-official:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/fetch_official_models.py

llm-agents:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_llm_agents.py

harvester-once:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.data_harvester --once

.PHONY: g4f-probe-api g4f-merge-probe
g4f-probe-api:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/g4f_probe_api.py --base $${G4F_API_BASE-http://127.0.0.1:8081} --limit $${G4F_PROBE_LIMIT-40} --update-working

g4f-merge-probe:
	PYTHONPATH=$$PWD/src $(PYTHON) - <<-'PY'
	from src.agents.g4f_model_watcher import merge_from_working_txt
	from pathlib import Path
	p = merge_from_working_txt(Path('data/llm/probe/working_results.txt'))
	print('Updated:', p)
	PY

.PHONY: macro-regime fuse-forecasts factory-run

macro-regime:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_macro_regime.py

fuse-forecasts:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/fuse_forecasts.py

factory-run:
	# Sequential, no orchestrator
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.data_harvester --once || true
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.g4f_model_watcher --refresh --limit $${G4F_LIMIT-8} || true
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_llm_agents.py || true
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_macro_regime.py || true
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/fuse_forecasts.py || true

.PHONY: risk-monitor memos

risk-monitor:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_risk_monitor.py

memos:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_memos.py

.PHONY: recession earnings

recession:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_recession.py

earnings:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/run_earnings.py

.PHONY: backfill-prices
backfill-prices:
	PYTHONPATH=$$PWD/src $(PYTHON) scripts/backfill_prices.py

.PHONY: ui-smoke
ui-smoke:
	# Requires: pip install playwright && python -m playwright install chromium
	UI_BASE=$${UI_BASE-http://localhost:5555} PYTHONPATH=$$PWD/src $(PYTHON) ops/ui/ui_smoke.py || true

.PHONY: ui-smoke-mcp
ui-smoke-mcp:
	# Requires: npm i -D @modelcontextprotocol/sdk and @playwright/mcp available via npx
	UI_BASE=$${UI_BASE-http://localhost:5555} node ops/ui/mcp_ui_smoke.mjs || true

.PHONY: sec-audit
sec-audit:
	bash ops/security/security_scan.sh

.PHONY: ui-start ui-stop ui-restart
ui-start:
	AF_UI_PORT=$${AF_UI_PORT-5555} bash scripts/ui_start.sh

ui-stop:
	bash scripts/ui_stop.sh

ui-restart:
	$(MAKE) ui-stop || true
	AF_UI_PORT=$${AF_UI_PORT-5555} bash scripts/ui_start.sh

.PHONY: ui-start-bg ui-restart-bg ui-status ui-logs
ui-start-bg:
	AF_UI_PORT=$${AF_UI_PORT-5555} bash scripts/ui_start_bg.sh

ui-restart-bg:
	AF_UI_PORT=$${AF_UI_PORT-5555} bash scripts/ui_restart_bg.sh

ui-status:
	AF_UI_PORT=$${AF_UI_PORT-5555} bash scripts/ui_status.sh

ui-logs:
	tail -f logs/ui/streamlit_$${AF_UI_PORT-5555}.log

# --- New Streamlit skeleton (separate from canonical 5555) ---
.PHONY: streamlit-run streamlit-test streamlit-shots streamlit-lint

STREAMLIT_PORT ?= 5566

streamlit-run:
	AF_UI_PORT=$${STREAMLIT_PORT} PYTHONPATH=$$PWD/src streamlit run src/apps/streamlit/app.py --server.port $${STREAMLIT_PORT} --server.headless false

streamlit-test:
	STREAMLIT_PORT=$${STREAMLIT_PORT-5566} PYTHONPATH=$$PWD/src $(PYTHON) ops/ui/streamlit_smoke.py

streamlit-shots:
	@echo "[stub] add playwright screenshots for streamlit skeleton"

streamlit-lint:
	@echo "[stub] ruff/mypy for streamlit skeleton"

# --- Launch specific legacy Streamlit apps (for comparison) ---
.PHONY: streamlit-forecast-start streamlit-forecast-stop
streamlit-forecast-start:
	AF_UI_PORT=5556 AF_UI_APP=src/apps/forecast_app.py bash scripts/ui_start_bg.sh
streamlit-forecast-stop:
	AF_UI_APP=src/apps/forecast_app.py bash scripts/ui_stop_app.sh || true

.PHONY: streamlit-forecast-restart
streamlit-forecast-restart:
	$(MAKE) streamlit-forecast-stop || true
	$(MAKE) streamlit-forecast-start

.PHONY: streamlit-stock-start streamlit-stock-stop
streamlit-stock-start:
	AF_UI_PORT=5557 AF_UI_APP=src/apps/stock_analysis_app.py bash scripts/ui_start_bg.sh
streamlit-stock-stop:
	AF_UI_APP=src/apps/stock_analysis_app.py bash scripts/ui_stop_app.sh || true

.PHONY: streamlit-stock-restart
streamlit-stock-restart:
	$(MAKE) streamlit-stock-stop || true
	$(MAKE) streamlit-stock-start

.PHONY: streamlit-macro-start streamlit-macro-stop
streamlit-macro-start:
	AF_UI_PORT=5558 AF_UI_APP=src/apps/macro_sector_app.py bash scripts/ui_start_bg.sh
streamlit-macro-stop:
	AF_UI_APP=src/apps/macro_sector_app.py bash scripts/ui_stop_app.sh || true

.PHONY: streamlit-macro-restart
streamlit-macro-restart:
	$(MAKE) streamlit-macro-stop || true
	$(MAKE) streamlit-macro-start

.PHONY: streamlit-apps-start streamlit-apps-stop
streamlit-apps-start: streamlit-forecast-start streamlit-stock-start streamlit-macro-start
streamlit-apps-stop: streamlit-forecast-stop streamlit-stock-stop streamlit-macro-stop

.PHONY: streamlit-apps-restart
streamlit-apps-restart:
	$(MAKE) streamlit-apps-stop || true
	$(MAKE) streamlit-apps-start

# Restart everything (canonical Streamlit 5555 + legacy Streamlit apps + Dash) with fixed ports
.PHONY: apps-full-restart
apps-full-restart:
	$(MAKE) streamlit-apps-stop || true
	$(MAKE) dash-stop || true
	$(MAKE) ui-restart-bg
	$(MAKE) streamlit-apps-start
	$(MAKE) dash-restart-bg

# --- Dash (experimental UI) ---
.PHONY: dash-start
dash-start:
	AF_DASH_PORT=$${AF_DASH_PORT-8050} PYTHONPATH=$$PWD:$$PWD/src $(PYTHON) src/dash_app/app.py

.PHONY: dash-smoke
dash-smoke:
	PYTHONPATH=$$PWD/src $(PYTHON) ops/ui/dash_smoke.py

.PHONY: dash-start-bg dash-restart-bg dash-status dash-logs
dash-start-bg:
	AF_DASH_PORT=$${AF_DASH_PORT-8050} bash scripts/dash_start_bg.sh

dash-restart-bg:
	AF_DASH_PORT=$${AF_DASH_PORT-8050} bash scripts/dash_restart_bg.sh

dash-status:
	AF_DASH_PORT=$${AF_DASH_PORT-8050} bash scripts/dash_status.sh

dash-logs:
	tail -f logs/dash/dash_$${AF_DASH_PORT-8050}.log

.PHONY: dash-stop dash-restart
dash-stop:
	bash scripts/dash_stop.sh

dash-restart:
	bash scripts/dash_restart_bg.sh

.PHONY: dash-mcp-test
dash-mcp-test:
	node ops/ui/mcp_dash_smoke.mjs || true

# --- UI Health (Playwright) ---
.PHONY: ui-health-setup ui-health

ui-health-setup:
	# Installs Playwright Chromium for UI health report
	npm i -D playwright || true
	npx playwright install chromium

ui-health:
	# Generate UI health report JSON + screenshots
	DASH_BASE=$${DASH_BASE-http://127.0.0.1:8050} node ops/ui/ui_health_report.mjs || true

# --- UI DEV ---
.PHONY: open-ui dash-dev dash-start-and-open
open-ui:
	python -c "import webbrowser; webbrowser.open('http://127.0.0.1:8050')"

dash-dev:
	PYTHONPATH=$$PWD:$$PWD/src FLASK_ENV=development DASH_DEBUG=1 \
	python -m src.dash_app.app

dash-start-and-open: dash-start-bg open-ui

# --- Logged wrappers ---
.PHONY: log-dash-smoke log-ui-health
log-dash-smoke:
	PYTHONPATH=$$PWD/src python -m ops.run_and_log make dash-smoke

log-ui-health:
	PYTHONPATH=$$PWD/src python -m ops.run_and_log make ui-health

# --- Git hooks ---
.PHONY: git-hooks
git-hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-push || true

# --- Pack artifacts ---
.PHONY: artifacts-zip
artifacts-zip:
	PYTHONPATH=$$PWD/src python -m ops.pack_artifacts

# --- API docs ---
.PHONY: api-docs-generate
api-docs-generate:
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python ops/docs/generate_api_docs.py ; \
	else \
		echo "[api-docs] venv python not found. Run: python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt" ; \
	fi

# --- LLM Summary (hourly partitions) ---
.PHONY: llm-summary-run llm-summary-hourly llm-summary-scheduler-start
llm-summary-run:
	PYTHONPATH=$$PWD/src python -m src.agents.llm.run_once

llm-summary-hourly:
	watch -n 3600 make llm-summary-run

llm-summary-scheduler-start:
	PYTHONPATH=$$PWD/src python -m src.agent_runner.scheduler

# --- Minimal agent orchestrator (sequential) ---
.PHONY: agent-run-once
agent-run-once:
	PYTHONPATH=$$PWD/src python -m src.agents.orchestrator

.PHONY: snap-url
snap-url:
	# Take a Playwright screenshot of a single URL
	# Usage: make snap-url URL=http://localhost:5556 OUT=artifacts/ui_health/legacy.png
	URL=$${URL-http://127.0.0.1:8050} OUT=$${OUT-artifacts/ui_health/snap.png} node ops/ui/snap_url.mjs || true

# --- Full refresh pipeline and restart (parallel agents)
.PHONY: refresh-all
refresh-all:
	bash scripts/refresh_all_and_restart.sh

.PHONY: ui-watch
ui-watch:
	AF_UI_PORT=$${AF_UI_PORT-5555} AF_UI_WATCH_INTERVAL=$${AF_UI_WATCH_INTERVAL-5} bash scripts/ui_watch.sh

.PHONY: net-observe net-sni-log
net-observe:
	PYTHONPATH=$$PWD/src $(PYTHON) ops/net/net_observe.py --interval $${NET_INTERVAL-5} --samples $${NET_SAMPLES-0}

net-sni-log:
	IFACE=$${IFACE-en0} OUTDIR=$${OUTDIR-artifacts/net} bash ops/net/tls_sni_log.sh

.PHONY: searx-probe
searx-probe:
	PYTHONPATH=$$PWD/src $(PYTHON) ops/web/searxng_probe.py --runs $${SEARX_PROBE_RUNS-12} --sleep $${SEARX_PROBE_SLEEP-0.5}

.PHONY: searx-up searx-down searx-logs
searx-up:
	docker compose -f ops/web/searxng-local/docker-compose.yml up -d
	@echo "SearXNG local on http://localhost:8082 (export SEARXNG_LOCAL_URL=http://localhost:8082)"

searx-down:
	docker compose -f ops/web/searxng-local/docker-compose.yml down

searx-logs:
	docker compose -f ops/web/searxng-local/docker-compose.yml logs -f

# --- LLM context + forecast (for Judge)
.PHONY: llm-context llm-forecast

llm-context:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.llm_context_builder_agent

llm-forecast:
	$(PYTHON) scripts/llm_forecast_agent.py

# --- Forecast agents (no orchestrator; callable via Makefile/cron) ---
.PHONY: equity-forecast forecast-aggregate

equity-forecast:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.equity_forecast_agent

forecast-aggregate:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.forecast_aggregator_agent

.PHONY: backtest evaluate commodity-forecast

backtest:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.backtest_agent

evaluate:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.evaluation_agent

commodity-forecast:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.commodity_forecast_agent

# --- Macro & freshness agents ---
.PHONY: macro-forecast update-monitor

macro-forecast:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.macro_forecast_agent

update-monitor:
	PYTHONPATH=$$PWD/src $(PYTHON) -m src.agents.update_monitor_agent
