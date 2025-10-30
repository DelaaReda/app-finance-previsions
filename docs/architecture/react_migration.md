# Migration UI vers React — Plan Professionnel

Objectif
- Migrer l’UI vers React (Vite + TypeScript) en conservant Dash/Streamlit pour la transition (Strangler pattern).
- API REST sous Flask (dans le serveur Dash) expose `/api/*`.

Phases
1. Cadrage & Contrats
- Contrats d’API par page (schéma JSON minimal) + critères de parité.
- Feature flags: activer `/react` en parallèle.

2. API Layer (Flask)
- Déjà disponible: `/api/health`, `/api/forecasts`, `/api/news`, `/api/watchlist` (GET/POST), `/api/settings` (GET/POST), `/api/llm/judge/run`.
- À ajouter: `/api/dashboard/kpis`, `/api/backtests`, `/api/evaluation`, `/api/regimes`, `/api/risk`, `/api/recession`, `/api/notes`, `/api/memos`.
- Tests API (pytest), snapshots JSON.

3. Migration Pages
- Ordre business: Forecasts → LLM Judge → Dashboard → News → Watchlist/Settings → Backtests → Evaluation → Regimes/Risk/Recession.
- Parité fonctionnelle, empty‑states FR, exports, perfs (<2s), accessibilité.

4. Observabilité & Qualité
- Logs actions (trace_id), Profiler JSONL, OTel (4318) optionnel.
- e2e Playwright (Forecasts/Judge/Dashboard), CI build React + tests.

5. Bascule & Rollback
- Basculer le trafic par paliers via flag. Rollback = routeurs Dash conservés.

Runbook Dev
- Backend API: `make dash-restart-bg` → `GET /api/health`.
- Frontend React: `make react-dev` → http://127.0.0.1:5173 (proxy `/api`).
- Logs: `make dash-fore` (console), `make dash-logs`, `make ui-otel-follow` (collector + Dash).

Acceptation par page
- Parité, schéma stable, latences P95 < 500ms, tests API + e2e verts, logs d’actions présents.

Risques & Mitigation
- Données absentes → empty-states + doc `factory-run`.
- Temps LLM → timeouts + logs + feedback UI.
- Perf SSR/CSR → pagination/virtualisation + cache API léger.

Livrables Sprint N
- API Dashboard/Backtests + tests.
- Pages React Dashboard/Backtests + e2e.
- CI build + tests API/e2e.
