# React Integration Architecture

But: une UI React moderne, testable, consommant l’API Flask/Dash sans complexifier le backend Python.

Principes
- Contrats clairs: OpenAPI (`docs/api/openapi.yaml`) → types générés pour React.
- Découplage: React ne lit pas le FS; il consomme uniquement `/api/*`.
- Idempotence data: UI lit les dernières partitions `data/**/dt=*` via l’API (
  la production des partitions reste orchestrée par `Makefile`/CRON).

Backend (Dash/Flask)
- Routes `/api/*` dans `src/dash_app/app.py` qui appellent `src/dash_app/api.py`.
- CORS permissif en dev; en prod, restreindre à l’origin du frontend.
- Logging/trace: `X-Trace-Id` propagé; profiler JSONL + OTel (optionnel).
- Endpoints nivelés par page (KISS):
  - Aggregations légères (ex: KPIs, top‑N) et pagination simple si nécessaire.
  - Aucune logique de présentation (le tri/formatage se fait client si léger).

Frontend (React — Vite + TS)
- `src/api/client.ts`: wrappers fetch (GET/POST) + header `X-Trace-Id`.
- `src/app/providers.tsx`: React Query provider (cache + retries), Devtools.
- Pages `src/pages/*`: chargent via `useQuery` et affichent états `loading/error`.
- Types: `webapp/src/shared/types.d.ts` généré depuis OpenAPI; validation (zod) optionnelle côté client.
- Vite proxy: `/api` → `http://127.0.0.1:8050` (dev only).

Déploiement
- Option A (simple): servir le build React via Flask (`/react/*` → `webapp/dist/`).
- Option B (recommandée): Nginx en front (React build + reverse proxy `/api` → Dash), Dash derrière (gunicorn/uvicorn).

Sécurité & Gouvernance
- Pas de secrets dans le frontend; toutes les opérations sensibles passent par l’API.
- Rate limiting de base côté Flask (LLM endpoints) + timeouts.
- Versionner les schémas (OpenAPI) quand on casse la compat.

Workflow Dev
- `make dash-restart-bg` → API up
- `make react-dev` → React up
- Types: `npx openapi-typescript docs/api/openapi.yaml -o webapp/src/shared/types.d.ts`
- e2e: Playwright (pages clés) + smoke HTTP (`make dash-smoke`)

How‑to: ajouter une page React
- Créer `webapp/src/pages/NewPage.tsx`
- Ajouter la route dans `webapp/src/App.tsx`
- Si besoin API: ajouter la route dans `src/dash_app/app.py` + implémenter `src/dash_app/api.py`
- Documenter dans `docs/api/openapi.yaml` → générer types
- Empty‑states + FR + logs d’actions (via client.ts)

Notes Migration
- Dash reste pour Admin/Observabilité durant la transition.
- Streamlit conservé en legacy (5555) le temps des validations.
