# ARCHITECTURE_MAP.md

## Source of Truth (Current)
- Backend API entrypoint: `apps/api/src/platform/main.py`
- Backend runner: `apps/api/src/platform/run_api.py` (wrapper via `finance-copilot.sh`)
- Frontend app: `apps/web/src/`
- Jobs/automation: `apps/api/src/platform/legacy/jobs/` (runtime exécuté via `apps/api/runtime/copilot.sh`)
- Runtime data snapshots: `apps/api/runtime/data/`
- Runtime caches: `apps/api/runtime/cache/`

## Canonical App Layout
- Backend runtime code: `apps/api/src/`
- Backend orchestration: `apps/api/runtime/copilot.sh`
- Frontend app: `apps/web/src/domains/`
- Shared documentation: `docs/`
- Orchestrator: `docs/orchestrator-ops/`

## Import and Path Policy
- Exécuter via `apps/api/src` (ou `apps/api/runtime/copilot.sh`) pour que `data/*` et `cache/*` pointent vers le runtime.
- Aliases de compatibilité autorisés:
  - `apps/api/src/data` -> `apps/api/runtime/data`
  - `apps/api/src/cache` -> `apps/api/runtime/cache`
  - `data` -> `apps/api/runtime/data` (legacy root compatibility)
  - `cache` -> `apps/api/runtime/cache` (legacy root compatibility)
- Pas de nouveaux répertoires produits hors `apps/*` pour la logique applicative.

## Architecture Style
- Canon: **Vertical Slice + Domain-First APIs**.
- Les routes orchestrent uniquement.
- Les services/domaines contiennent la logique métier et réutilisable.

## Modules de référence
- Références de réutilisation: `docs/ops/REUSE_MODULES_CATALOG.md`
- Standards endpoint/contrat/quality: `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`

## MVP Endpoints (v1)
- `GET /api/health`
- `GET /api/forecasts`
- `GET /api/stocks/prices`
- `GET /api/news/feed`
- `POST /api/copilot/ask`
- `GET /api/judge`

## Règle Frontend
- Les écrans MVP consomment uniquement API backend en mode nominal.
- Le mode mock n’est autorisé qu’en DEV/TÉTAT d’échec contrôlé, avec badge explicite.
