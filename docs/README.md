Project Docs — Finance Agent

Quickstart

- Dash (nouvelle UI — actuelle)
  - Port par défaut: `8050`.
  - Démarrer (BG): `make dash-start-bg`
  - Redémarrer (BG): `make dash-restart-bg`
  - Statut/Logs: `make dash-status` / `make dash-logs`
  - Smoke test: `make dash-smoke` (codes 200) ; MCP: `make dash-smoke-mcp` (Playwright MCP)
  - Hot reload: lancer avec `AF_DASH_DEBUG=true`.

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
