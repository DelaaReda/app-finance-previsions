Project Docs — Finance Agent

Quickstart

- Dash (nouvelle UI — actuelle)
  - Port par défaut: `8050`.
  - Démarrer (BG): `make dash-start-bg`
  - Redémarrer (BG): `make dash-restart-bg`
  - Statut/Logs: `make dash-status` / `make dash-logs`
  - Smoke test: `make dash-smoke` (codes 200) ; MCP: `make dash-smoke-mcp` (Playwright MCP)
  - Hot reload: lancer avec `AF_DASH_DEBUG=true`.
- OpenTelemetry (optionnel):
    - Tout‑en‑un: `make ui-otel-restart` → (tente) démarrer le collector (4318) et redémarre Dash instrumenté (8050) avec health‑check. Si Docker indisponible, bascule automatiquement en exporter `console` (traces visibles dans les logs Dash).
    - Démarrages séparés:
      - Collector: `make otel-up` (compose sous `ops/otel/`), logs: `make otel-logs`, arrêt: `make otel-down`. Sur macOS: lancez Docker Desktop (`open -a Docker`) au préalable.
      - Dash instrumenté: `make dash-restart-otel-bg` (ou `make dash-start-otel-bg`).
    - Variables utiles: `OTEL_EXPORTER_OTLP_ENDPOINT` (défaut `http://127.0.0.1:4318`), `OTEL_SERVICE_NAME`, `OTEL_PYTHON_LOG_CORRELATION=true`, `DASH_HOT_RELOAD=false`.

  - Logs en console (foreground):
    - Sans OTel: `make dash-fore` (debug ON, profiler ON, hot‑reload OFF).
    - Avec OTel (console par défaut): `make ui-otel-fore`.
    - Niveau configurable: `AF_LOG_LEVEL=INFO`.

  - Suivi live des logs (BG):
    - Dash uniquement: `make dash-logs`
    - Dash + Collector: `make ui-otel-follow` (si Docker actif)

- React (nouveau frontend)
  - Dev server: `make react-dev` (Vite sur `http://127.0.0.1:5173`, proxy `/api` → Dash `8050`).
  - Build: `make react-build`, preview: `make react-preview`.
  - API fournies par le serveur Dash/Flask (mêmes process):
    - `GET /api/forecasts?asset_type=all|equity|commodity&horizon=all|1w|1m|1y&search=...&sort_by=score`
    - `GET /api/news?sector=all|tech|finance|energy&search=...`
    - `GET /api/watchlist`, `POST /api/watchlist {"tickers":["AAPL","MSFT"]}`
    - `GET /api/settings`, `POST /api/settings {"move_abs_pct":1.0,"tilt":"balanced"}`
    - `POST /api/llm/judge/run {"model":"...","max_er":0.08,"min_conf":0.6,"tickers":"AAPL,MSFT"}`
  - Types API (OpenAPI): `docs/api/openapi.yaml` → `npx openapi-typescript docs/api/openapi.yaml -o webapp/src/shared/types.d.ts`
  - Guide junior React: `docs/dev-junior/react_onboarding.md` et `docs/architecture/react_integration.md`


- Streamlit (ancienne UI — legacy, pas de nouvelles features)
  - Port: `5555`. Démarrer: `make ui-start`, Redémarrer: `make ui-restart`.
  - Mode BG: `make ui-start-bg` / `make ui-restart-bg` (logs `logs/ui/streamlit_5555.log`).
  - Statut/Logs: `make ui-status` / `make ui-logs`.
  - Maintenance ponctuelle uniquement pendant la migration vers Dash.

- Redémarrer tout (Dash + Streamlit): `make apps-full-restart`
  - Canonique 5555 (`src/apps/agent_app.py`) + legacy 5556/5557/5558 + Dash 8050.

MCP & Codex CLI
- Codex config: `~/.codex/config.toml` (browser MCP, architecture analyzer, filesystem, memory, mermaid, sqlite, serper/tavily/firecrawl, spec‑workflow, taskmanager, FRED/Finnhub, Playwright MCP).
- First time: Node/npm required; Playwright MCP downloads browsers on first run.
- Runbook and prompts: `runbook/codex_playbook.md`.

Docs Map
- Product: `product/backlog.md` — EPICs, user stories, acceptance criteria.
- Architecture: `architecture/vision.md`, `architecture/c4.md`, `architecture/refactor_plan.md`.
- Architecture (UI): `architecture/dash_migration.md` — migration Streamlit → Dash (Dash = cible).
- UI: `ui/ui_audit.md` — audit, decisions, and action plan.
- Progress: `PROGRESS.md` — what’s done, what’s next, run discipline.
- QA: `qa/ATLAS_QA.md` — procedure for ATLAS to verify commits, restart UI, test pages, and report.
- Team process: `dev/team-process.md` — multi‑agents workflow (dev/arch/qa), PR/issue templates, CI & pre‑commit

Dev Workflow (Codex)
- **After changements UI/Sprint** : relancer l'UI (`make dash-restart-bg`), lancer `make dash-mcp-test` pour évaluation UX IA (rapports sous `data/reports/`, corrections si erreurs).
- Commit modèle : `Sprint-X: feat(dash): [desc] ; tests ui: make dash-mcp-test` (corrige erreurs avant push final).

Principles
- No central orchestrator in runtime UI. Pipelines run via `Makefile`/cron; UI reads latest partitions under `data/**/dt=YYYYMMDD/`.
- Safe UI by default: no shell/make prompts in user flows; admin‑only guidance lives in Agents Status/docs.
- French language first; consistent copy, friendly empty states, and confirmations after writes.
