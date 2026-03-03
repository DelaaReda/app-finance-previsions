# Finance Copilot – Guide rapide (Architecture 2026)

## 🏗️ Nouvelle Architecture (Post-Migration Feb 2026)

**Structure cible:**
- Backend: `apps/api/src/` (ex: `copilot-app/backend/`)
- Frontend: `apps/web/src/` (ex: `copilot-app/frontend/`)
- Runtime: `apps/api/runtime/` (data, cache, logs)
- Platform: `platform/` (config, automation, policies)
- Packages: `packages/` (contracts, sdk, ui-kit)
- Archive: `archive/` (ancienne structure)

**Documentation:**
- Architecture: `docs/architecture/AGENT_ONBOARDING.md`
- Workspace Index: `docs/ops/AGENT_WORKSPACE_INDEX.md`
- Migration Summary: `docs/ops/MIGRATION_SUMMARY.md`

---

## Démarrer / arrêter
- (Re)lancer backend + jobs + frontend statique :
  ```bash
  ./finance-copilot.sh restart
  ```
- Arrêter :
  ```bash
  ./finance-copilot.sh stop
  ```

## URLs
- Backend : http://localhost:8050
  Docs : http://localhost:8050/docs
- Frontend statique : http://localhost:5173 (servi depuis `apps/web/src/domains/forecasts/pages`)

## Endpoints utiles (curl)
- Santé :
  `curl -s http://localhost:8050/api/health`
- Judge (LLM) :
  `curl -s 'http://localhost:8050/api/judge?limit=1' | jq`

## Logs
- Backend : `apps/api/runtime/api.log`
  (Inclut les requêtes/réponses LLM : `judge_llm_request`, `judge_llm_raw_response`).
- Frontend statique : `/tmp/frontend.log`

## Structure active
- Code backend : `apps/api/src/domains/...` (API FastAPI, services, analytics).
- Plan de structure pour agents : `docs/architecture/AGENT_ONBOARDING.md` et `docs/ops/AGENT_WORKSPACE_INDEX.md`.
- Entrée API unique : `apps/api/src/platform/main.py` (lancement via `apps/api/src/platform/run_api.py`).
- Jobs (ingest/news/macro/judge_enrich) : `apps/api/src/platform/legacy/jobs/` (lancés par le script).
- Données (snapshots) : `apps/api/runtime/data/` (alias `data/` et `apps/api/src/data`).
- Cache runtime : `apps/api/runtime/cache/` (alias `cache/`).
- Frontend statique : `apps/web/src/domains/forecasts` (fichiers HTML/CSS/JS, pas de build Vite).
- Anciennes variantes archivées : `archive/`.

## Référence bonnes pratiques (exemple)
- Standard endpoints/API (contrat stable, cache, fallback, tests):
  `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`
- Gouvernance d'exécution globale (gates/process):
  `docs/ops/ENGINEERING_PLAYBOOK.md`

## Dépendances / env
- Variables : `apps/api/src/.env` (OPEN_ROUTER_API_KEY, clés FRED, etc.).
- Installer manquants (ex : feedparser, duckdb) :
  ```bash
  cd apps/api/src
  .venv/bin/pip install feedparser duckdb
  ```

## Tests rapides (manuels)
- Health : `curl -s http://localhost:8050/api/health`
- Judge : `curl -s 'http://localhost:8050/api/judge?limit=1' | jq`
- Gate backend standard (agents) :
  - sans checks live : `./scripts/backend_regression_gate.sh --no-live`
  - avec checks live : `./scripts/backend_regression_gate.sh`

## Mise a Jour 2026-03-03 (Hotfix)
- Orchestration resynchronisee:
  - `BATCH-05`: `IN_PROGRESS`
  - `BATCH-06`: `WAITING_DEP` (`depends_on=BATCH-05`)
  - `BATCH-07`: `WAITING_DEP` (`depends_on=BATCH-06`)
- Fichiers source de verite:
  - `docs/operations/orchestrator/priority-queue.json`
  - `docs/operations/orchestrator/parallel-workstreams.json`
  - `docs/product/planning/WORKSTATE.md`
- Forecast fallback corrige (`apps/api/src/platform/legacy/jobs/forecasts_simple.py`):
  - ordre de fallback: history/cache -> `price` vs `previous_close` -> `change_percent`.
  - evite les inversions de direction quand l'historique est absent.
- Validation rapide:
  ```bash
  cd apps/api/src
  PYTHONPATH=. pytest -q platform/legacy/jobs/tests/test_forecasts_simple.py
  ```

## Notes
- Pas de build frontend : le script sert directement `apps/web/src` via `python -m http.server 5173`.
- Les jobs s'exécutent au démarrage (news, sentiment, judge_enrich, macro).
- **Migration Feb 2026:** Architecture refactorisée vers domain-driven design. Voir `docs/ops/MIGRATION_SUMMARY.md`.

## Claude Desktop Deep Troubleshoot
- Runbook: `docs/ops/CLAUDE_DESKTOP_DEEP_TROUBLESHOOT.md`
- Primary command:
  ```bash
  scripts/use-claude-deep-troubleshoot.sh
  ```
- Compatibility alias:
  ```bash
  scripts/use-claude-deep-troobleshoot.sh
  ```

## Claude Desktop UI I/O (Input -> Output)
- Runbook: `docs/ops/CLAUDE_DESKTOP_UI_IO.md`
- One command:
  ```bash
  scripts/claude_desktop_ui_io.sh --input "repond pong puis liste actions en 3 puces"
  ```
- Choose chat behavior:
  ```bash
  scripts/claude_desktop_ui_io.sh --input "..." --chat-mode same
  scripts/claude_desktop_ui_io.sh --input "..." --chat-mode new
  ```
- Long task tracking:
  ```bash
  scripts/claude_desktop_ui_io.sh --input "..." --max-wait 420 --poll 15
  ```
- Auto-handle permission prompts while running:
  ```bash
  scripts/claude_desktop_ui_io.sh --input "..." --auto-always-allow
  ```
- Permanent MCP config (no repeated authorization popups):
  ```bash
  scripts/claude_desktop_configure_always_allow.sh
  ```
- YOLO mode (aggressive no-permission flow):
  ```bash
  scripts/claude_desktop_enable_yolo_mode.sh
  ```
- Output artifacts:
  - `*.input.txt`
  - `*.response.txt`
  - `*.actions.txt`
  - `*.meta.env`
